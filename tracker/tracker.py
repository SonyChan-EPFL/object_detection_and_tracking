import pandas as pd
import numpy as np
import glob
import sys
import os
import math
import argparse
from scipy.spatial import distance
from scipy.optimize import linear_sum_assignment




# 
# Use hungrain algorithm to track the vehicles 
# Read from {scene}_all.txt and output to {scene}_tracked_all.txt
# Input format: "frame",'cls_no', 'xc', 'yc', 'w', 'h'
# Output format: "frame",'cls_no', "id", 'xc', 'yc', 'w', 'h', 'infer'
#

def to_pixel_coordinate(img_h, img_w ,token, offset=0):
    x_c = float(token[offset + 1]) * img_w
    y_c =float(token[offset + 2]) * img_h
    w = float(token[offset + 3]) * img_w
    h = float(token[offset + 4]) * img_h
    return (x_c, y_c, w, h)


def textfile_to_array(file_name, img_w, img_h, dtype=float):    
    with open(file_name) as file:
        lines = file.readlines()
        data = [line.strip().split() for line in lines]
        data = [list(map(float, x[:2]))+ [-1.0] + list(to_pixel_coordinate(img_h, img_w ,x, 1)) + [0.0] for x in data ]
        data = np.array(data, dtype=dtype)      
    return data

def get_bbox_position(arr, dtype=float):
    return dtype(arr[0]+arr[2]/2), dtype(arr[1]+arr[3])

def merge_trajectories(df):
    
    idxs = pd.unique(df["id"])
    id_ranges = [(idx, df.loc[df['id'] ==idx]["frame"].min(), df.loc[df['id'] == idx]["frame"].max()) for idx in idxs]
    correct_df = df.copy()

    
    # Seek for wrongly splitted trajectories
    wrong_list = []
    wrong_idxs = []
    for idx, _, e in id_ranges:
        x = df.loc[(df['id'] ==idx) & (df['frame'] == e) ]['xc'].values[0]
        y = df.loc[(df['id'] ==idx) & (df['frame'] == e) ]['yc'].values[0]
        id_in_next_frame = filter(lambda x: x[0] != idx and x[1] == e + 1, id_ranges)
        for idx_n, s_n, _ in id_in_next_frame:
            x_n = df.loc[(df['id'] ==idx_n) & (df['frame'] == s_n) ]['xc'].values[0]
            y_n = df.loc[(df['id'] ==idx_n) & (df['frame'] == s_n) ]['yc'].values[0]
            dist = math.sqrt((x-x_n)**2 + (y-y_n)**2)
            # If distance between the centers of two bounding boxes is less than 20 pixel 
            if dist < 5:
                wrong_list.append((idx,idx_n))
                wrong_idxs.append(idx)
                # print("id:{}, id_n{}".format(idx, idx_n))
    
    # Trace the linkages among the wrong trajectories 
    # Eg. 11 <- 34 , 34 <- 44, Both 34 and 44 need to be assign to 11.
    reassigned = []
    correct_dict = {}
    wrong_idxs.sort()
    for w_idx in wrong_idxs:
        if w_idx not in reassigned:
            pre_w_idx = w_idx
            while len(list(filter(lambda x: x[0] == pre_w_idx, wrong_list))) != 0:
                _, wn_idx = list(filter(lambda x: x[0] == pre_w_idx, wrong_list))[0]
                if w_idx not in correct_dict.keys():
                    correct_dict[w_idx] = [wn_idx]
                else:
                    correct_dict[w_idx].append(wn_idx)
                reassigned.append(wn_idx)
                pre_w_idx = wn_idx
    # print(correct_dict)
    
    # Assign wrong id to correct one
    for k, idx_list in correct_dict.items():
      for idx in idx_list:
        correct_df.loc[correct_df["id"] == idx, "id"] = k
    
    # Re-assign sequence of ids, starting from 0
    for k, idx in enumerate(list(pd.unique(correct_df['id']))):
        correct_df.loc[correct_df["id"] == idx, "id"] = k

    return correct_df


def major_vote_for_class(df):
    grouped = df.groupby("id")
    for uid, group in  grouped:
        votes = np.unique(group['cls_no'], return_counts=True)
        true_class = max(list(zip(votes[0], votes[1])), key=lambda x : x[1])[0]
        df.loc[df.id==uid, 'cls_no'] = true_class
    return df

def linear_interpolation(df):
    def box_close_to_edge(pre_row, img_w, img_h, offset):
        pre_xc = pre_row.xc.values[0]
        pre_yc = pre_row.yc.values[0]
        pre_w = pre_row.w.values[0]
        pre_h = pre_row.h.values[0]
        x_s = pre_xc - pre_w / 2
        x_e = pre_xc + pre_w / 2
        y_s = pre_yc - pre_h / 2
        y_e = pre_yc - pre_h / 2
        return x_s <= offset and x_e >= (img_w-offset) and y_s <= offset and y_e >= (img_h-offset)  
    
    
    grouped_id = df.groupby('id')
    for idx, df_f in grouped_id:
        total_frames = df_f['frame'].max() - df_f['frame'].min() + 1
        if len(df_f) != total_frames:
            frame_ids = sorted(df_f.frame.values)
            pre = frame_ids[0] - 1
            for idx,f in enumerate(frame_ids):
                pre_row = df_f.loc[df_f['frame'] == pre]
                f_row = df_f.loc[df_f['frame'] == f]
                if pre != f - 1:
                    if (idx > 10 and not box_close_to_edge(pre_row, 3840, 2160, 25)) or idx <= 10:
                        pre_xc = pre_row.xc.values[0]
                        pre_yc = pre_row.yc.values[0]
                        f_xc = f_row.xc.values[0]
                        f_yc = f_row.yc.values[0]

                        x_dist = f_xc - pre_xc
                        y_dist = f_yc - pre_yc

                        for p in range(pre + 1, f):
                            ratio = (p - pre) / (f - pre)
                            p_xc = pre_row.xc.values[0] + int(x_dist * ratio)
                            p_yc = pre_row.yc.values[0] + int(y_dist * ratio)
                            s = pd.Series({'frame': int(p) , 'cls_no': int(pre_row.cls_no.values[0]), 'id': int(pre_row.id.values[0]),
                                        "xc": p_xc, "yc": p_yc, "w": pre_row.w.values[0], "h": pre_row.h.values[0], "infer": 1})
                            df = df.append(s, ignore_index=True)
                pre = f
    return df.sort_values(by=['frame'])


if __name__ == "__main__":

    # Parse arguments
    # in_filepath = sys.argv[1] 
    # max_distance = 100
    # max_lifetime = 20
    # img_w = 3840
    # img_h = 2160
    # start_frame = 1
    # class_infer = True
    # linear_infer = True
    # track_cls = "0,1,2,3,4"
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', type=str, help='Annotation txt file path')
    parser.add_argument('--img_w', '-iw', type=int, default=3840, help='Image width Default=3480')
    parser.add_argument('--img_h', '-ih', type=int, default= 2160, help='Image height Default=2160')
    parser.add_argument('--max_distance', '-md', type=int, default=100, help='Max distance between consecutive bounding boxes  Default=100')
    parser.add_argument('--max_frame', '-mf', type=int, default=20, help='Max frame to track bounding box Default=20')
    parser.add_argument('--start_frame', '-sf', type=int, default=1, help='Frame number where to start tracking Default=1 ')
    parser.add_argument('--track_cls', '-tc', type=str, default="0,1,2,3,4", help='Class number to track Default="0,1,2,3,4"')
    parser.add_argument('--class_infer', '-ci',
        action="store_true", default=False, help='Infer class within a trajectory')
    parser.add_argument('--linear_infer', '-li',
        action="store_true", default=False, help='Infer missing bounding box within a trajectory')

    opt = parser.parse_args()


    
    # Load annotation from file
    df = textfile_to_array(opt.input, opt.img_w, opt.img_h, float)
    df = sorted(df, key=lambda x : x[0])
    df = pd.DataFrame(df, columns=["frame",'cls_no', "id", 'xc', 'yc', 'w', 'h', 'infer'])
    track_cls_list = opt.track_cls.split(',')
    df_not_tracked = df.loc[~df['cls_no'].isin(track_cls_list)]
    df = df.loc[df['cls_no'].isin(track_cls_list)]

    # initialize label for time t=0
    print("Running Hungarian tracker on {}".format(opt.input))
    Y = [[i for i in range(len(df[df["frame"] == opt.start_frame]))]]
    buf = []
    for t in range(opt.start_frame, int(df["frame"].max())):
    # for t in range(start_frame, start_frame+ 3):
          
        # get the bounding boxes at time t and t+1
        # x1 is t
        # x2 is t+1
        x1 = df[df["frame"] == t][["xc", "yc"]].values
        x2 = df[df["frame"] == t+1][["xc", "yc"]].values
        x1 = np.array([(bbox[0], bbox[1]) for bbox in x1])
        x2 = np.array([(bbox[0], bbox[1]) for bbox in x2]) 
            
        # append Y for time t+1
        Y.append([-1 for i in range(np.shape(x2)[0])])
        # append items in buffer to x1 (coordinates) 
        x1_buf = list(x1)
        for b in buf:
            x1_buf.append(b[2])
        x1_buf = np.array(x1_buf)
        
            
        # - compute the distances between all vehicles at time t (and in the buffer) to time t+1
        # - then compute the optimal assignment
        # *** only compute assignments if x2 is not empty
        row_index = []
        col_index = []
        if(np.shape(x2)[0] != 0):      
            
            # compute the optimal assignments between x1 and x2 first
            row_index_priority = []
            col_index_priority = []
            row_assigned = []
            col_assigned = []
            if(np.shape(x1)[0] != 0):
                distances_priority = distance.cdist(x1, x2, 'euclidean')
                row_index_priority, col_index_priority = linear_sum_assignment(distances_priority)
                for r,c in zip(row_index_priority, col_index_priority):
                    # assign labels from time t to t+1
                    if(distances_priority[r][c] < opt.max_distance):
                        Y[-1][c] = Y[-2][r]  
                        row_assigned.append(r)
                        col_assigned.append(c)
                    
            # now compute the optimal assignments between x1_buf and x2 without double assignments
            # set the distances between the previously matched objects to a very small number to force them to match again
            if(np.shape(x1_buf)[0] != 0):
                distances = distance.cdist(x1_buf, x2, 'euclidean')        
                for r,c in zip(row_assigned, col_assigned):
                    distances[r][c] = -999999             
                row_index, col_index = linear_sum_assignment(distances)
                rm = []
                for r,c in zip(row_index, col_index):
                    # assign labels from time t to t+1
                    #if(r < np.shape(x1)[0]):
                    #    if(distances[r][c] < 50):
                    #        Y[-1][c] = Y[-2][r]  
                    # assign labels from buffer to t+1
                    # then remove them
                    if(r >= np.shape(x1)[0]):
                        if(distances[r][c] < opt.max_distance):
                            buf_ind = r - np.shape(x1)[0]
                            rm.append(buf_ind)
                            Y[-1][c] = Y[buf[buf_ind][0]][buf[buf_ind][1]]
                # remove items from buffer that were assigned
                buf_temp = []
                for i,b in enumerate(buf):
                    if(i not in rm):
                        buf_temp.append(b)
                buf = buf_temp.copy()
                    
        # *** only compute assignments if x2 is not empty
                
        # iterate through x1 and check if it has been assigned to an object in x2
        # if not then add it to the buffer
        for i in range(np.shape(x1)[0]):
            if(i not in row_index):
                tup = (-2, i, x1[i]) # (timestamp, index of object in x1, coordinates)
                buf.append(tup)
                
        # give new label to unassigned objects in x2
        # these are (most probably) newly found objects
        for i in range(len(Y[-1])):
            if(Y[-1][i] == -1):
                # print(np.amax([y for yy in Y for y in yy]))
                Y[-1][i] = np.amax([y for yy in Y for y in yy]) + 1
                
        # increment timestamps
        for i in range(len(buf)):
            buf[i] = (buf[i][0] - 1, buf[i][1], buf[i][2])
            
        # remove items from buffer that has exceeded the maximum lifetime
        rm = []
        for i,b in enumerate(buf):
            if(b[0] < -1*opt.max_frame):
                rm.append(i)
        buf_temp = []
        for i,b in enumerate(buf):
            if(i not in rm):
                buf_temp.append(b)
        buf = buf_temp.copy()

    # rewrite ground truth with label
    print("Assigning labels....")
    for t,y in enumerate(Y):    
        df.loc[df["frame"] == t+opt.start_frame,"id"] = y
    
    
    # change column type
    df = df.astype(int)

    print("Merge wrongly separeted trajectories....")
    df = merge_trajectories(df)
    
    # Enhance the result
    # Use major vote to unify the class of an id
    if opt.class_infer:
        print("Inferring the class in in a trajectory.....")
        df = major_vote_for_class(df)
    
    # Do linear interpolation to fill up the missing bounding box
    if opt.linear_infer:
        print("Doing linear interpolation in a trajectory.....")
        df = linear_interpolation(df)
    
    # Add not_tracked object back
    df = pd.concat([df, df_not_tracked], ignore_index=True)

    # change column type
    df = df.astype(int)

    output_filename = opt.input.replace('_all.txt',"_tracked_all.txt")
    print("Save result to {}".format(output_filename))
    df.to_csv(output_filename, sep=" ", header=False, index=False)