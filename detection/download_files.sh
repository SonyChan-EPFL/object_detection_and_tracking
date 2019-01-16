#!/bin/bash


echo "Downloading object_detection.tar.gz...."
gfileid="1MyNYp-APTvHTwUke7YA7zIqAfjnx5bYA"
destination_dir="./"
file_name="object_detection.tar.gz"
destination_path="${destination_dir}${file_name}"
curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${gfileid}" > /dev/null
curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${gfileid}" -o ${destination_path}

echo "Downloading aerial_dataset_version2.tar.gz...."
gfileid="1rUcUKc8Vgs8wERgDnG1FfHHDl8Q7hu-I"
destination_dir="./"
dataset_name="aerial_dataset_version2.tar.gz"
destination_path="${destination_dir}${dataset_name}"
curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${gfileid}" > /dev/null
curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${gfileid}" -o ${destination_path}


echo "Inflating the ${file_name}....."
tar -zxf $file_name

echo "Inflating the ${dataset_name}....."
tar -zxf $dataset_name

echo "Moving files to corresponding directories...."
folder="object_detection"
mv aerial_dataset/ darknet/aerial_dataset/
mv ${folder}/data/ yolov3/data/
rm -rf yolov3/weights yolov3/yolo_cfg yolov3/data
rm -rf darknet/weights darknet/yolo_cfg darknet/aerial_dataset
cp -R ${folder}/weights yolov3/
cp -R ${folder}/yolo_cfg yolov3/
cp -R ${folder}/weights darknet/
cp -R ${folder}/yolo_cfg darknet/

echo "Removing uneccessary files"
rm -rf $file_name $dataset_name folder cookie

echo "Done!"
