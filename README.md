# Histogram-Based Image Brightness and Contrast Analysis

## Abstract

Digital images captured under insufficient or uneven illumination may suffer from poor brightness and low contrast, making visual details and object boundaries difficult to identify. This project proposes a histogram-based approach for analysing image brightness and contrast. For each input image, the system computes the grayscale histogram, mean gray level, and standard deviation to identify dark, overexposed, or low-contrast conditions. Gamma Correction and Contrast Stretching are then applied to improve image appearance according to the detected condition. The effectiveness of each enhancement method is evaluated by comparing image statistics, histograms, and Canny edge-detection results before and after processing. The expected outcome is a simple tool that recommends an appropriate enhancement method while showing whether the improved brightness and contrast also produce clearer and more meaningful edges.

**Keywords:** Image enhancement, histogram analysis, brightness, contrast, Gamma Correction, Contrast Stretching, Canny edge detection.

## Sample Visualization

![Two sample images with grayscale histograms](assets/sample_cover_histograms.png)
