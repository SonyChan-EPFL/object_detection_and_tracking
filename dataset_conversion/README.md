# Dataset Conversion
```
    ├── README.md                         
    └── dataset_conversion.ipynb  : Notebook for creating aerail_dataset (Version2)
```
# Introduction 
**dataset_conversion.ipynb** contains the preprocessing code that coverts the annotations of other datasets into yolo annotation.

### **Download Link**: [Version1](https://drive.google.com/file/d/1lD9By9aSsRZs2rHy5-Up67bul4A4kulY/view?usp=sharing) [Version2](https://drive.google.com/file/d/1rUcUKc8Vgs8wERgDnG1FfHHDl8Q7hu-I/view?usp=sharing)

#### Version1: Less objects in cyclist and pedestrian class (Current model was trained by this version)

#### Version2: Augmented the objects in cyclist and pedestrian class

## Here are the list of the dataset:
1. CARPK_devkit & PUCPR+_devkit
2. Vehicules1024
3. Aerial
4. VisDron2018
5. UAV-benchmark-M
6. Stanford Drone Dataset 

## Class number:
```
0 -> car
1 -> truck
2 -> bus
3 -> van
4 -> cyclist
5 -> pedestrian
```

## Yolo annotation format:
```
<object-class> <x> <y> <width> <height>
<object-class> - integer number of object from 0 to (classes-1)
<x> <y> <width> <height> - float values relative to width and height of image, it can be equal from (0.0 to 1.0]
for example: <x> = <absolute_x> / <image_width> or <height> = <absolute_height> / <image_height>
atention: <x> <y> - are center of rectangle (are not top-left corner)
```

