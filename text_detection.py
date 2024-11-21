import cv2
import numpy as np
from paddleocr import PaddleOCR,draw_ocr
import skimage.filters as filters
import re
import argparse

#initialize argparse 
parser = argparse.ArgumentParser()

#define arguments
parser.add_argument("image_list", metavar="image_path", type=str, nargs= "+", help="path of image(s) to be read")

args = parser.parse_args()

# Initialize EasyOCR reader
ocr = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=False)

#for loop to read each image passed as arguments
for file in args.image_list:
    # read image, convert it to grayscale, apply blur and convert to binary
    image = cv2.imread(file)
    inverted_image = 255 - image
    gray_image = cv2.cvtColor(inverted_image,cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray_image,20,50,50)

    # divide gray by morphology image
    division = cv2.divide(gray_image, blurred, scale=255)

    # sharpen using unsharp masking
    sharp = filters.unsharp_mask(division, radius=1.5, amount=1.5, preserve_range=False)
    sharp = (255*sharp).clip(0,255).astype(np.uint8)

    # Apply thresholding (create binary image)
    ret, thresholded = cv2.threshold (255-sharp, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # attempts to preprocess the image for better countour detection (successfully failed!)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
    dilate = cv2.dilate(thresholded, kernel, iterations=4)

    # brightness/contrast adjustment --> cuurently not in use (did not improve anything)
    alpha = 0.9 # Contrast control (1.0-3.0)
    beta = -15 # Brightness control (0-100)
    adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


    # docstring of HoughCircles: HoughCircles(image, method, dp, minDist[, circles[, param1[, param2[, minRadius[, maxRadius]]]]]) -> circles
    minDist = 100 #19
    param1 = 20 #31
    param2 = 40 #40 #smaller value-> more false circles
    minRadius = 12 #10
    maxRadius = 80 #79

    circles = cv2.HoughCircles(blurred, 
                            cv2.HOUGH_GRADIENT, 
                            1, 
                            minDist, 
                            param1=param1, 
                            param2=param2, 
                            minRadius=minRadius, 
                            maxRadius=maxRadius
                            )
    codes = []
    failed_codes = []

    if circles is not None:
        circles = np.uint16(np.around(circles))
        for circle in circles[0,:]: #this for loop is for every lid
            # print(circle)
            x = circle[0]
            y = circle[1]
            r = circle[2]
            # Calculate the bounding box coordinates == squares
            top_left_x = x - r
            top_left_y = y - r
            bottom_right_x = x + r
            bottom_right_y = y + r

            # Create parameters for the squares
            w = bottom_right_x - top_left_x
            h = bottom_right_y - top_left_y

            # Extract the square ROI from the image
            ROI = image[top_left_y:bottom_right_y, top_left_x:bottom_right_x]

            # Draw the bounding box on the original image
            img = cv2.rectangle(image, (top_left_x, top_left_y), (top_left_x + w, top_left_y + h), (0, 255, 0), 2)

            coordinates = []
            coordinates.extend([top_left_x, top_left_y, w, h])
            result = ocr.ocr(ROI, cls=False)
            for item in result: #this for loop is for everything that is detected inside the cap
                if item is not None:
                    string = "" #before the for loop, you define an output (e.g. empty string) where to store the processed data gained with the for loop
                    for i in range(len(result[0])): #this for loop is for every line detected in each square
                        substring = result[0][i][1][0]
                        cleaned_str = re.sub("[^A-Za-z0-9]+", "", substring) #substitute special characters with nothing
                        if re.match("^[A-Z0-9]+$", cleaned_str) and not re.match("^[0-9]+$", cleaned_str):
                            if len(cleaned_str) == 3:
                                string += cleaned_str
                            else:
                                string += "_" + cleaned_str + "_"
                            
                    #if "i" in string:
                    corrected_str = (re.sub("i", "1", string)) #--> substitute ("what you have", "with what you want", where (in this case string))
                    #if "O" in string:
                    corrected_str = (re.sub("O", "D", corrected_str)) 
                    # print(coordinates)
                    if len(string) == 9: #the previous for loop was in the frame of each single cap. Now we check the resulting string
                        codes.extend([[coordinates, corrected_str]])
                    else:
                        failed_codes.extend([[coordinates, corrected_str]])

    for cap in codes + failed_codes:
        if cap in failed_codes:
            text_color = (0, 0, 255)
        else:
            text_color = (255, 0, 0)
        cv2.putText(img, cap[1], (cap[0][0], cap[0][1] + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7 , text_color, 2, cv2.LINE_AA)

    print("Codes:") #the print is outside of every for loop because we want to print all the strings (=not single caps or ROIs, but the whole picture)
    print(codes)
    print("Failed codes:")
    print(failed_codes)

    filename = re.sub("\.[A-Za-z]+", ".txt", file)
    txt_file = open(filename, "a") #"a" == append
    for code in codes:
        print(code[1])
        txt_file.write(code[1] + "\n")
    txt_file.close()
  
    # Save modified image as new file
    recognized_filename = re.sub("(\.[A-Za-z]+)", "_recognized\\1", file)
    cv2.imwrite(recognized_filename, img)

