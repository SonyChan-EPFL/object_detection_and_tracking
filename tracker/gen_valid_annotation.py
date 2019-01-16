import os
import numpy as np
import pandas as pd
import argparse



# 
# Filter the desired bounding boxes for each frame that are inside the desired sementic segmentation 
# Input: 
# 
# If no sementic segmentation information is provided, the output will be the same as the input
#



def to_pixel_coordinate(img_h, img_w ,yolo_str):
    token = yolo_str.split()
    x_c = float(token[1]) * img_w
    y_c =float(token[2]) * img_h
    w = float(token[3]) * img_w
    h = float(token[4]) * img_h
    return (x_c, y_c, w, h)

def load_segmentation(path):
    return np.load(path)

def valid_bbox(seg, class_no, bbox, img_w, img_h, edge_offset, tolerance_thrs):
    x_c, y_c, w, h = bbox
    x_s = int(x_c - w / 2)
    x_e = int(x_c + w / 2) + 1
    y_s = int(y_c - h / 2)
    y_e = int(y_c + h / 2) + 1
    
   
    if class_no == 5:
    # if the object class is pedestrian, it should be on sidewalk or cross walk
      if seg[int(y_c)][int(x_c)] in [2,3]:
        return True
    else:
    # Other objects should be on the road or cross walk
      if box_inside_image(x_s, x_e, y_s, y_e, img_w, img_h,edge_offset):
          if seg[int(y_c)][int(x_c)] in [0,1]:
              return True
          else:
              region = seg[y_s:y_e, x_s:x_e]
              count_in, count_out = seg_class_vote(region)
              ratio = count_in / region.size
              if ratio > tolerance_thrs:
                  return True
    return False

def box_inside_image(x_s, x_e, y_s, y_e, img_w, img_h, offset):
    return x_s >= offset and x_e <= (img_w-offset) and y_s >= offset and y_e <= (img_h-offset)    

def seg_class_vote(region):
    count_in = 0
    count_out = 0
    result = np.unique(region, return_counts=True)
    for i, count in zip(result[0], result[1]):
        if i == 3:
            count_out += count
        else:
            count_in += count
    return count_in, count_out


if __name__ == "__main__":
  
  # Parse arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('--img_w', '-iw', type=int, default=3840, help='Image width Default=3480')
  parser.add_argument('--img_h', '-ih', type=int, default= 2160, help='Image height Default=2160')
  parser.add_argument('--folder', '-f', type=str, help='Folder that contains annotations txt files')
  parser.add_argument('--seg_path', '-sp', type=str, help='Segmentation array in npy format')
  parser.add_argument('--edge_offset', '-e', type=int, default=25, help='Ignore bbox which edges are close to bounding of \
        images in pixels Default=25' )
  parser.add_argument('--tolerance_th', '-t', type=float, default=0.9, help='Tolerance threshold i.e \
        desired class counts / total pixels Default=0.9')
  parser.add_argument('--save_individually', '-si',
        action="store_true", default=False, help='Save annotation separately in {folder_name}_filtered/')

  opt = parser.parse_args()
  
  
  
  # Load list of txt files
  txt_list = [file for file in os.listdir(opt.folder) if file.endswith('.txt') and not file.endswith("_all.txt")]
  txt_list = sorted(txt_list, key=lambda x: int(x.split("_")[-1].split(".")[0]))

  # Set output txt file name
  output_file_name = "_".join(txt_list[0].split("_")[:-1]) + "_all.txt"
  
  # Load sementic segmentation information
  if opt.seg_path:
    seg  = load_segmentation(opt.seg_path)

  if opt.save_individually:
    # Create output directory if not exits
    output_path = opt.folder[:-1] + "_filtered/"
    if not os.path.isdir(output_path):
      os.mkdir(output_path)
    

  with open(opt.folder + output_file_name, "w+") as fo:
      # for each txt file
      for txt in txt_list:
          new_anno = []
          frame_no = txt.split("_")[-1].split(".")[0]
          with open(opt.folder + txt) as fi:
              lines = fi.readlines()
              for line in lines:
                  line = line.strip()
                  class_no = int(line.split()[0])
                  bbox = to_pixel_coordinate(opt.img_h, opt.img_w, line)
                  if seg is not None:
                    if valid_bbox(seg, class_no, bbox, opt.img_w, opt.img_h, opt.edge_offset, opt.tolerance_th):
                      fo.write(frame_no + " " + line + "\n")
                  else:
                    fo.write(frame_no + " " + line + "\n")
                  if opt.save_individually:
                    new_anno.append(line)
          # Save the filtered results in seperated files (frame by frame)
          if opt.save_individually:
            with open(output_path + txt, "w+") as output:
              output.write("\n".join(new_anno))
  print("Save result to {}".format(opt.folder + output_file_name))