import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import math
import argparse
import os
import sys
import subprocess

#
# Plot the tracked bounding boxes frame by frame
# Input: {scene}_tracked_all.txt, folder of images
# Ouput: folder of images with bounding boxes
#

def load_class_names(path):
    with open(path) as file:
        return [ cls.strip() for cls in file.readlines() if len(cls) > 0]
    
def drawrect(drawcontext, xy, outline=None, width=0):
    x1, y1, x2, y2 = xy
    points = (x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)
    drawcontext.line(points, fill=outline, width=width)

def drawtext(img, pos, text, bgcolor=(255,255,255), font=None):
    if font is None:
        font = ImageFont.load_default().font
    (tw, th) = font.getsize(text)
    box_img = Image.new('RGBA', (tw, th), bgcolor)
    ImageDraw.Draw(box_img).text((0, 0), text, fill=(0,0,0,255), font=font)
    img.paste(box_img, (round(pos[0].item()), round(pos[1].item() - th -2)))

def get_id_colors(no_uid):
    return [tuple(np.random.choice(range(256), size=3)) for i in range(no_uid + 1)]

def plot_tracked_boxes(img, boxes, no_uids, class_names, id_colors, hide_lp):
    width = img.width
    height = img.height
    draw = ImageDraw.Draw(img)
    rgb_infer = (0, 0, 0)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font=None
    for box in boxes:
        cls_id = int(box[0])
        uid = int(box[1])
        is_infer = box[6] == 1 
        # if is_infer and hide_lp:
        #     continue
        if uid != -1:
            x1,y1,x2,y2 = (box[2] - box[4]/2.0), (box[3] - box[5]/2.0), \
                    (box[2] + box[4]/2.0), (box[3] + box[5]/2.0)
            
            rgb = id_colors[uid] #(red, green, blue)
            if hide_lp:
                rgb_box = rgb
            else:
                rgb_box = rgb if not is_infer else rgb_infer
            
        else:
            rgb = (255, 255, 255)
            rgb_box = rgb
        text = "{}, {}".format(class_names[cls_id],uid)
        drawtext(img, (x1, y1), text, bgcolor=rgb, font=font)
        drawrect(draw, [x1, y1, x2, y2], outline=rgb_box, width=4)

if __name__ == "__main__":
  
  # Parse arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('--anno_path', '-ap', type=str, help='Annotation txt file path')
  parser.add_argument('--img_path', '-ip', type=str, help='Folder that contains all frames')
  parser.add_argument('--output_path', '-op', type=str, help='Folder that contains output frames')
  parser.add_argument('--class_path', '-cp', type=str, help='Class names file')
  parser.add_argument('--img_tmp', '-it', type=str, help='Naming rule of the input images \
    it should be python format string. eg. "Echabdens_Route_de_la_Gare_5_{:06d}.jpg"')
  parser.add_argument('--output_img_tmp', '-ot', type=str, help='Naming rule of the output images,\
    it should be python format string. eg. "Echabdens_Route_de_la_Gare_5_{:06d}.jpg"')
  parser.add_argument('--font', '-f', type=str, default="/System/Library/Fonts/Helvetica.ttc",
       help='The path of text font default=/System/Library/Fonts/Helvetica.ttc (Mac)')
  parser.add_argument('--font_size', '-fs', type=int, default=30, help='Text size default=30')
  parser.add_argument('--hide_linear_interpolation', '-hl',
        action="store_true", default=False, help='Set color the inferred bounding to be identical with the original one ')

  opt = parser.parse_args()

  # Set the parameters
  path = opt.anno_path 
  img_path = opt.img_path
  output_path =  opt.output_path
  img_tmp =  opt.img_tmp
  output_img_tmp = opt.output_img_tmp 
  font_path = opt.font
  font_size = opt.font_size


  # Create output folder if no exits
  if not os.path.isdir(output_path):
      os.mkdir(output_path)

  # Load name of classes from "class.names"
  class_names = load_class_names(opt.class_path)

  # Load annotation text file
  df = pd.read_csv(path, delimiter=" ", header=None, dtype=int)
  no_uids = len(df[6].unique())
  start_frames = df[0].min()
  last_frames = df[0].max()
  no_ids = len(df[2].unique())
  id_colors = get_id_colors(no_ids)
  # for each frame
  for i in range(start_frames, last_frames + 1):
      save_name = output_path + output_img_tmp.format(i)
      img = Image.open(img_path + img_tmp.format(i))
      df_i = df[df[0] == i]
      if len(df_i) > 0 :
          boxes = df_i.values[:, 1:]
          plot_tracked_boxes(img, boxes, no_uids, class_names, id_colors, opt.hide_linear_interpolation)
      print("save plot results to {}".format(save_name))
      img.save(save_name)