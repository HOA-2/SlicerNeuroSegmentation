# General Subcortical Brain Segmentation using 3D Slicer
Brain segmentation is a process by which the different parts of an MRI image of a brain are separated from each other using outlines. The resulting geometric metrics are then used to calculate statistically useful measures such as volume, thickness, or surface area.  This procedure is typically performed for a number of brains belonging to several experimental groups and can be used to test the hypothesis that specific brain structures from two populations of subjects is different. Segmentation requires a decent knowledge of neuroanatomy, but much of this knowledge can be acquired during the segmentation process. The goal of this manual and method is to provide a means by which efficient morphometric analysis can be performed.

## Basics of segmentation
Slicer is a program that creates visual images of the brain in the coronal, axial, and sagittal planes and displays them on the same screen.  This makes it easy to cross-reference a point you are not sure about.  3D Slicer is used for segmentation and parcellation of the brain.  This guide presumes that 3D Slicer is installed on your computer ([https://www.slicer.org](https://www.slicer.org). 3D Slicer is a powerful tool to evaluate MRI images.  It is a constantly evolving program that contains a large number of modules to serve different types of users.
<img src="https://lh3.googleusercontent.com/U1nWRSyztLl3OZz4_wlc3pFSF1R1c86p7Q477drMq6qTLiBiy6Z6aUlWYB8eIxs0gMmNA-9v0wuf" alt="" title="Slicer Welcome">

When 3D Slicer is first opened, a screen similar to the one displayed above will appear.  It contains three main regions.  The main toolbar is a row of buttons, dropdown menus and commands.   Here is where common operations are accessed, such as commands to load data (white arrow) and save data (after clicking the double arrows to the right of the load button).  On the welcome screen, the load data button can also be found on the left hand side of the main screen (lower white arrow).  On the right hand part of the screen, four windows are present.  The window with the blue background will show a 3D rendering of your data, and the three windows in black will each display a cardinal view of the MRI image - one view is in the axial plane, one is in the sagittal plane, and one is in the coronal plane.

At its core, 3D Slicer is a visualization tool linked to a large number of modules.  Modules are constantly being improved and added.  For segmentation, there are three main modules that will be used: Segment Editor, Segmentations, and Volumes. Access these using the drop-down menu in the Main Toolbar.  The three main modules are indicated by yellow arrows in the image below.

<img src="https://lh3.googleusercontent.com/M1z1aWNbloMilrX34w1RpEnHh5P84g5n-kLKT2tBG1YA103bd77YC-CFwvzcsBoJelESz5uY9Xxw" alt="" title="Modules">

The Segment Editor Module contains tools to name and outline segments of the brain.  The Segmentations Module contains commands to adjust the appearance of the segments (e.g., make them visible or invisible; change their opacity or border line width).  The Volumes Module contains information about the MRI volume, including the number of slices and resolution.  It also contains adjustable brightness and contrast.

### 1. Loading files
To begin, you will load two image sets from the same case.  The first is the T1 weighted image set, and the second is a T2 weighted image set.  The ‘T’ refers to the relaxation time that is measured. T1 refers to the longitudinal relaxation time and T2 refers to the transverse relaxation time it takes for protons to return to equilibrium after the radiofrequency pulse.  For our purposes, images acquired with a T1 weight accentuates certain tissue properties, while T2-weighted images represent different tissue properties.  Both are useful for visualizing and drawing boundaries, although the T1 weighted images are conventionally used for segmentation.

Load the T1 and a T2 weighted image sets (usually with an ‘acpc_restore’ somewhere in the file name) for a specific case. This presumes an appropriate image is downloaded and located in a folder on your computer, and that it is has been intensity-corrected and spatially normalized.  If you do not observe ‘acpc-restore’ in the file name, ask for assistance in locating the correct normalized image. Click on the load button, and navigate to the T1 file and open it.  If you do not see the four visualization windows, click on the button next to the arrow button in the main toolbar and select Four-Up.

After a brief loading window, three images should appear, one for each orthogonal viewing plane of the brain.  The red window typically contains images in the axial plane (i.e., a cut parallel to the ground), the yellow window contains images in the sagittal plane (i.e., a cut perpendicular to the ground cutting from the front of the head (anterior) to the back (posterior)), and the green window shows images in the coronal plane (i.e., a cut at a right angle to the ground cutting from the left side of the skull/brain to the right side).  Use the bars above each window to cycle through the images.  These images are of the same volume, and it is often of utility to view a structure in all three images at once.  To facilitate this, click on the Crosshair button, which is located on the Main toolbar on the far right.  Position your mouse over any image and depress and hold the shift key.  Moving around the mouse will move around crosshairs on the image such that the center of the crosshair is at your mouse point, and the crosshair center and the planes of cut in the other views will move in register.

Go to the Segment Editor module in the module selector dropdown menu in the main toolbar.  Notice that the entire left part of the window will now be filled with new buttons and drop down menus.  Using the menu on the left, create a new segmentation, and name it according to the case and the segmentation you are about to perform. Add your initials. For example, for general segmentation of Case 398860, name the segmentation Case398860Gen_RJR, where RJR are your initials.  For the master volume, select the T1 file.

Go to the Volumes module, go to the bottom of the screen and write down the contrast and brightness values (known here as window (W) and level (L).  Also, note the threshold values.  Record these values in an excel spreadsheet. This spreadsheet is also good for any observations you may have about the brain. Also, it is useful to uncheck the interpolation box – this will allow you to see the real (unsmoothed) data.  There are two ways to change the smoothed image to unsmoothed.  The first is a checkbox in the volume module (under the ‘Display’ heading). The second is a box located on the drop-down menu of the active image (click on the push pin at the top of the image).  Next to the image name, you will see a depressed checkerboard icon – click on this to unselect.

### 2. Segment Names
Go to the Segment Editor, click on ‘add’. In the table underneath, a name will appear, called Segment 1.  To the left is an eye, which makes the segment visible or not visible.  Next to that is the color and the name.  If you double click on the name, you can rename the segment identity.  If you click on the color box, a second window will pop up.  Here you can again click on the color to change it, and rename things. However, this is also where you can select names and colors that have already been entered into the system. Sometimes this has been pre-loaded. In the case it is not, click on the left hand arrowhead, an operation which will expand the window.  Click on the folder icon on the upper right that just appeared, and use this to navigate to the Dropbox/GeneralSegmentation/JSON/ folder.  Load the file named, “SegmentationCategoryTypeModifier-GeneralSegmentation”.  Then hit OK and OK in the subsequent windows.  You should now have access to the correct segments.  If you need access to the dropbox, let someone know.

A Note About Radiological Imaging.  You may notice that Figure 1 (above) is labeled as The Left Lateral Ventricle.  The arrow is in fact in the left lateral ventricle. This isn’t a mistake!  Brain orientation is standardized according to a radiological convention; namely, that you are viewing the brain from the perspective of standing at the foot of the bed of a patient. Viewed this way, the ***left*** side of the patient is on the ***right*** of the screen. A good way to remind yourself (initially, at least) is to attach ‘Left’ and ‘Right’ post-its on your monitor.

## The Lateral Ventricle
The segmentation process starts with the lateral ventricle.  Select the Lateral Ventricle Left segment on the list in the Segment Editor Module.

The lateral ventricle is an oddly-shaped space within each brain hemisphere filled with cerebrospinal fluid (CSF).  It will appear black on the T1 images and it has an unusual three dimensional shape (Figure 1).  In the figure below, the brain has been removed to show the shape of the brain ventricles.  The lateral ventricles are two – one on each side under the cerebral hemispheres.  There is also a third ventricle and a fourth ventricle, and we’ll come to those in due time.  In the figure below, observe that each lateral ventricle has several parts – each part is under a region of the cerebral cortex.  The curved portion on the left is the anterior horn and is under the frontal lobe.  The pointy portion on the right hand side of the figure is beneath the occipital lobe and is referred to as the posterior (or occipital) horn.  The part that ends down and to the left is the inferior horn and is under the temporal lobe.

<img src="https://lh3.googleusercontent.com/vA8uq_176oPZKvgr6_VjglQtOWUcbsbJM4-j5mhruoaLeUaIQvinEFaC08Gs4G3ycakEympP8tOx" alt="enter image description here" title="Figure 1: Lateral Ventricle">

First, find the lateral ventricle. Go to a coronal view of a part of the ventricle, where it is relatively nicely sized (slide the bar at the top of the image window until you see a picture similar to the image below).  The interior of the ventricle is marked by the tip of a red arrow. In this section, the upper border is the white matter (axons) of the corpus callosum, which appears as a white structure.  The lateral and inferior border is a gray matter structure called the caudate nucleus that bulges into the ventricle.

<img src="https://lh3.googleusercontent.com/0H7EpYX62qS0bQDv1GDCtSKQovnnkxkZtkxYKc_QDc_GtA2Cy-2ADGZxnOfKVGP5-h9iSv9YEeHn" alt="" title="Figure 2: The Left Lateral Ventricle">

Now you know what the ventricle looks like, move the coronal images to the front of the brain where the structure first appears (you know it is the front of the brain if you can see the eyes below the brain). Move back of the brain to see how the shape changes.
The fastest and most accurate way to segment each ventricle is to use the paint tool (image below, red circle) or the draw tool (to the right of the paint tool) in conjunction with the editable intensity range under the masking sub-tab (yellow circle).

<img src="https://lh3.googleusercontent.com/RnH_pBGd70-Yd8UGjS0-CXoCY9SBteFYonxCFW128im3-tsjcav58DSZ40Xe6m6uHFhhPk2ZrTAZ" alt="" title="Tools">

This approach will allow you to paint voxels that fall within a certain range of intensities (yellow box).  To find that range, you need to get a sense of which voxels should be included in the ventricle, and which should be included as part of the surrounding white or grey matter.  One way to do this is to select the pointer tab (labeled as ‘None’ under Effects in the figure above), and point the cursor at different voxels in the image.  The ventricle, on a T1 image, should have low values, and you should see the corresponding intensity values in the lower left-hand part of the window, under Data Probe (image above, white arrow; the number will appear on the far left of B).

Use this tool to get a sense of where the border is. Then set the lower editable intensity range to -0, and the upper limit to what you have decided (orange box). Then select a relatively large diameter paint tool, and paint the ventricles.  Only the voxels in the range should be selected.  Do this for one slice, for both gray and white matter, and then zoom out to evaluate.  If you see voxels that are dark and excluded from your ventricle outline, think about increasing your threshold.  If you see voxels in the ventricle segment that you think are light gray and should be included in gray matter, reduce your threshold.  Play around with this just a bit.

A more precise method exists that eliminates some of the guess-work of the previous one. If you click the threshold button (first icon in the second row in above image), you will observe that the whole image starts to slowly flicker. More accurately, an image overlay will cyclically become more and less transparent (image below). This overlay is tied to the intensity values that appear in a bar under threshold range (yellow box in figure above).

<img src="https://lh3.googleusercontent.com/0x-NVc0d06__hXFv5PGUuh7F_LjM6gJAUjzm3DVxChxv7-xMo7z2yY3fOu0zOzHbI7hK0_7LB3w3" alt="" title="Threshold">

This bar is adjustable.  So, similar to what you did in the previous paragraph, you can set the upper and lower bounds of the editable intensity range and see it in real time for whatever slice or slice orientation you care to view. This is much better because you can generate a threshold and see the implications for the whole structure, rather than determine it by looking at representation voxels.  Even better, when you have figured it out, you may simply click on the ‘Use for Masking’ button, and the range is automatically imported into the masking section.  Before you set the threshold, make sure you look at different images of the brain (coronal, sagittal, axial) to make sure you getting exactly what you need (not too much, not too little).

Now that you’ve played around with the tool and have a sense of how it works, we’ll apply it in a way that standardizes values across brains.  This will use a histogram threshold too.  You’ll find this once you click on the ‘Threshold’ tool in the Segment Editor.  Click on the arrow to the left of 'Local histogram. (If you don’t see this option, let someone know.)

Select the coronal view, and proceed to the anterior commissure until you see a section similar to the image below.  Select the box under local histogram, and draw it on the brain so it is similar in position to the yellow box seen in the figure below.  Once you do so, a histogram with two peaks will be generated on the left hand side of the window.  The left peak represents the voxels associated with the lateral ventricle and the right peak represents the voxels associated with the white matter.  Change the lower bound to “minimum” and the upper bound to “average.” You will see three lines. Click and hold on the first peak, and drag the mouse to the second (righthand peak). You will see that the orange line is in the middle of these two peaks. You have now created the threshold for the ventricles. Now, click the “use for masking” button.  This will now apply this threshold range to your segmenting tools. Record the upper bound that shows up under threshold range on the excel spreadsheet. Ideally, it should be between 500-600.

<img src="https://lh3.googleusercontent.com/3pRhdlkZ0z6l3DCDJO-kw59uSs2Uj2R3EiU3RrtSAOwHPHjseCSBk57XwkImWKcFjQhna-j8tYex" alt="enter image description here">

***Make sure that for each brain region, you record (in the excel spreadsheet) the threshold range so that it can be reproduced if needed.***
At this point, it is helpful to change some of the viewing settings of the segments. Go to the ***Segmentations*** module (found either in the large toolbar at the top, or via a shortcut from the segment editor module under the ‘master volume’ and to the right).  Under display, uncheck slice fill. Then go to advanced (located immediately below the slide bars) and increase the slice intersection thickness to 3px, or whatever you would like. Now go back to segment editor.
Now it is time to segment. Go to the most anterior section of the lateral ventricle, and then start segmenting.  If you are using the mouse, the paint tool may be the best.  If you are drawing with a pen, the draw tool is optimal.  Keep in mind that the draw tool will allow you to draw the contour around the structure of interest; an ‘enter’ key press is required to close and segment the structure.

As you progress posteriorly in the brain, the medial border of the ventricle will change from white matter to a small membrane (the septum pellucidum, double yellow arrows in the below figure) which separates one ventricle (red arrow) from the other.

<img src="https://lh3.googleusercontent.com/oR9-4B7sdJOfIqMVJRCEILkem4NVzT3JKowPQjKXXFZjpVPFSu83RCeox_TuZK4yybuyJeoS3qTh" alt="" title="Septum Pellucidum">

You’ll want to make sure you toe this line and not accidentally label voxels in the other ventricle.  You will also want to keep an eye out for other dark regions you may inadvertently label with your large brush – the black between the hemispheres above and below are common.  If you reliably get these extra voxels, click the erase tool and get rid of them, or press ‘z’ to undo.  If this is happening a lot, consider reducing the size of the brush (under the paint tool settings on the left, or just hit the ‘minus’ key).

When you are painting, it may help to check the ‘Sphere Brush’ under the settings (green circle in the below image).  This will give you a 3D brush and will paint in front and in back of the section you are selecting.

<img src="https://lh3.googleusercontent.com/RQA3KUmB6MMuKeiHdzMFYVHe9WjQchpJe7n4amvSAAKf23_Yg3hKYpVqWWlP7P1r9Y13lgKQAegr" alt="" title="sphere">

When you use this tool and as you go through the coronal sections, you will find that many of the voxels are already labeled when you get there.  Play around with this briefly to see if this is useful for you.  In some circumstances, this tool is nice and may save some work. Keep in mind, however, that as you proceed, you may label voxels that fall within the intensity criteria, but are outside the region you are interested in labeling.  In these cases, you will need to erase those voxels, which takes some time.  Also, keep in mind that erase also uses the sphere brush, and so when you erase with this checked, it will erase voxels in the slices in front and in back of the current one, and may undo some of the work you just did.  So, keep an eye out for aberrant voxels when you use this approach.  It may seem that the sphere brush may be too much work, rather than just going through the images carefully once per section.  However, if you use the sphere brush on a structure that goes from smaller to larger (and not in the reverse direction), it can be used easily and without fear of unintentional labeling.

A few hints on outlining.

1. Do not change the contrast or brightness willy-nilly.  If you inadvertently do, go to Volumes and reset the values you recorded at the beginning.  There are steps for parcellation that may benefit from changing the contrast or the brightness – feel free to change the contrast if it helps you to see things a bit better and aids in parcellation, but remember to go back to the original settings.

2. It is helpful to zoom in to see some voxels.  However, high magnification segmentation can be misleading. Be sure to zoom out and check your work when you are done with a section.

3. Mistakes are bound to be made but do your best to be precise and complete sections the first time. Going back has the potential to be time consuming and frustrating. You will minimize time and errors by trying to make sure that the boundaries are correct the first time around

4. Hotkeys are very useful. The keyboard number keys correspond to selecting and deselecting different tools.  For instance, pressing number 1 will select the paint tool, and pressing it again will return it to a cursor.  Similarly, the draw tool corresponds to number 2, and the erase to number 3.  The ‘z’ key is also important – pressing ‘z’ automatically undoes the last command.  Slicer has a memory, so you can hit this several times and it will undo several of your last commands.  You will develop your own technique.  I like to use my right hand on a mouse (or use a pen) to segment and use the mouse wheel to move through the sections.  I place my left ring finger on the ‘1’ key, the middle finger on the ‘2’ key, and the index finger on the ‘3’ key.  I curl the thumb underneath to put it on the z key.

5. Everyone develops their own way of doing things.  Play around.  If you find a faster (but still rigorous) way of segmenting a structure, let someone know!!

The ventricles are somewhat elaborated structures and are exist in the sagittal plane as a C-shape (see first figure in the ventricle section).  In this initial segmentation, concentrate only on the part in the front of the brain. There are two things to be aware of as you go from anterior to posterior. First, each lateral ventricle communicates with a small third ventricle, which is located below (inferior) the ventricles on the midline.  There is a small canal on either side, called the foramen of Monro, that is the connection (red arrows, figure below, left).  We consider this foramen to be part of the lateral ventricle parcellation, and the cigar-shaped third ventricle to be along the midline.  Second, it is important to pay attention to the borders of the ventricles as you move posteriorly.  About halfway through the brain, the lateral ventricles are flattened horizontal structures (lower figure, center).  Each ventricle is bounded medially by a little mustache – in the T1 images, it is white.  This is the fornix – one on either side (image below, center, yellow arrows).  It appears to begin superiorly, and progress inferiorly and flare out. Your segmentation should not go medial to this structure, or go below it.

<img src="https://lh3.googleusercontent.com/As3qw1L7qIf6kLhQ7qXtlp_-rGQ9v5XAOi1NwWaCtDcYo_EjJzvLCS_Ru1PkdhmjMScMp68sgMBL" alt="enter image description here" title="Figure 8">

A final consideration is that the ventricle extends from the frontal part of the brain, then loops down into the temporal lobe to make a C (refer to the drawing at the start of the ventricle section.  Before it does this, there is a large dilation in the ventricle (the atrium) from which the temporal extension of the ventricle (called the temporal, or inferior horn) emerges and proceeds towards the bottom and front of the brain (figure above, right).  The atrium also has a variable posterior extension that comes from it towards the back of the brain – this is the posterior (or occipital) horn.  In many cases, this appears to end, but be sure to keep looking at slices posteriorly because sometimes the ventricle opening is merely compressed and reappears more posteriorly.  An axial view is helpful for seeing the full ventricular extent.
Begin the segmentation at the anterior part of the ventricle and move posteriorly. Notice that since the threshold was set between white matter and the ventricle, the segmentation will look slightly incorrect between the ventricle and the caudate nucleus (gray matter structure lateral to the ventricle. That’s ok - we will revise this border when it comes to segmenting the caudate by creating a second threshold and creating an thresholded border between the caudate and the ventricle. For now, do not segment the inferior horn. We will do this separately when we start to think about structures lining the inferior horn (the hippocampus and the amygdala).  Segment the atrium so long as it is connected to the lateral ventricle you’ve been segmenting.  Keep moving posteriorly to segment the posterior horn, and don’t proceed anteriorly in the inferior horn.

After you go through the ventricle, it is time to go back and check your work.  You will do this with every structure, but the ventricles deserve a bit of extra caution.  There are likely to be unlabeled voxels within the ventricular segmentation.  These are voxels that aren’t as dark as the ventricle you thresholded and that often appear to be bulging into the ventricle or floating in the space. These voxels belong to the choroid plexus, the vascular structures that create the cerebrospinal fluid inside the ventricles.  By convention, we include the choroid plexus as part of the ventricle and therefore, these voxels need to be labeled.  These aggregations of choroid plexus are perhaps easier to identify posteriorly in the ventricle but are also seen more anteriorly (figure below).  Use the draw tool without the threshold to label the choroid plexus.  The pen is the most efficient way to segment this.

The importance of checking your segmentation in the axial, sagittal, and 3D views cannot be overstated.  A segmentation in the coronal view will produce jagged borders from one section to other section on the 3D.  The real anatomy of the ventricular is a smooth border, and the jaggedness misrepresents this anatomy.  The mismatch is due to partial voluming effects (~low resolution of voxels vs. brain structure boundaries)  and/or imprecision of the segment border.  A careful look on each of the other views eliminate most of these errors.  Start with the axial views, and make sure 1) the borders are smooth and consistent with the definition you set, and 2) there are no ‘holes’ in the structure (unlabeled voxels) or voxels that are outside the structure. Once the axial is complete, move to the saggital and do the same process.  Then do a quick scan of the coronal series to make sure that the changes you made on the other views didn’t alter the coronal borders.  It’s nice to have the four-panel viewing mode engaged so you can see the three-dimensional structure to identify issues (vide infra).

<img src="https://lh3.googleusercontent.com/7NNPqI1rMxe6Jrb8Z0JiyQAnsvh0EXeKD4daaDDKhnUU_Mqb9Vwdqxe6e_w7Z8X9RBYdp--Xt3fE" alt="" title="Choroid plexus">

If this isn’t already done, go up in the segment editor window and click on “Show 3D.”  This will reveal the 3D ventricle in the 3D window, and you can marvel.  In this window, click and drag inside the window to rotate and look at all aspects of the 3D ventricle.  This is a good place to check whether there are any inconsistencies, aberrant voxels you may have missed, coronal sections you sped through without sampling, etc.  If you’ve segmented the choroid plexus well, the undersurface will be smooth and not pock-marked. If you find that you have a pock-marked surface, use the crosshair tool in the menu bar. Select ‘basic crosshair.’ In four-pane viewing, you can press shift and move your cursor to get a specific location within the crosshair. If your images are linked, this will show you places that you may have missed voxels and have thus generated pock-marks.

Rotating and zooming around the image may leave the 3D model out of the plane or out of the window.  To get it back, go to the toolbar on top of the 3D window.  There should be an arrow, a number (1), and a crosshair.  Click the crosshair to center.  Then click on the arrow.  There are a lot of commands here, but the most useful (for taking pictures) is the axes with the letters on them (S,P,R,L,A,I).  Click on a letter, and the 3D model will snap to that perspective.  If you like it, feel free to take a picture.  On the big tool bar, click screenshot. Select 3D view, and name it.  IMPORTANT.  This just takes the picture but it does not save it. To do this, you will have to go to the left and click Save.  A dialog box will open. Unclick everything except the picture, select the folder, and you now have your very own ventricle picture.

Once you are done with each structure, please save the segmentation file.

## The Third Ventricle
The lateral ventricles are nice and big, and outlining gives you some experience with high contrast structures.  Now let’s turn to the third ventricle.  This ventricle has several appearances, depending on the image plane.

<img src="https://lh3.googleusercontent.com/4sWJxRa37DdOB1hT1s4d1qoajAkenEYwDtmPBiHqdcBbC81MAkrpzFxm7DVnSDuy-BCOucpzjfAN" alt="enter image description here" title="3rd V Modified from Nieuwenhuys 2008">

It is located along the midline in the center of the brain, and it extends from the optic chiasm anteriorly to the midbrain posteriorly. In the figure above, examine the third ventricle (to the right and below the arrow). Note that it has recesses inferiorly and anteriorly (#6 and #7) that make a W in the sagittal plane, and a similar set of recesses posteriorly and superiorly (#9 and #10).

Go to segment editor and add a new segment. Double click on the color and select ‘third ventricle’ in the dialog box.  You should use the threshold as generated above.

<img src="https://lh3.googleusercontent.com/MX7SDNPB3NY0fBN5auwBvLDUXAZsZqLEQZ-W4M1lYpFtERFAcGsmmEBGYZeVkrQUMEv3m-HG9mVn" alt="" title="Ant 3rd Ventricle, AC">

1. Anterior Portion.  In the coronal slice view, locate the anterior commissure (AC – figure above, blue arrow). Directly underneath the AC on the midline is the third ventricle.  Outline the third ventricle with the paint tool or the draw tool with the intensity range set at the same levels used for the lateral ventricles. The use of this intensity range will allow you to label the entire structure in one fell swoop, so long as the extent of the paint circle does not extend past the lower border of the brain.  If you accidentally extend past this boundary and label some voxels below the brain, you can correct it. Enter ‘z’ on your keyboard to undo your outlining or hit 3 (the erase hotkey) and erase those pesky voxels.  Then switch back to the paint tool.  Once you have outlined the 3rd ventricle, move anteriorly.  The optic tracts, which are lateral and lower than the 3rd ventricle, will now merge underneath the ventricle to form the optic chiasm.  You should be able to see the boundaries, but feel free to adjust the brightness and contrast to make it more visible should you have any difficulty spotting it. To do this, select the arrow under ‘Effects’ on the segment editor, or alternatively, if you are using the paint tool already, hit the number 1 again. This will deselect the paint tool and reselect to the arrow. Now go to the brain image, and click and drag the arrow on the image.  Dragging to the left and right will increase and decrease the image contrast, respectively, while dragging up and down will decrease and increase the brightness.  
***n.b. Later editions of slicer have a toggle button to turn this on - it’s on the main toolbar to the right of the Window selector button (it’s called ‘Window’/level)***  
At the next anterior level, the optic chiasm will disconnect from the brain, and above it will be a teardrop-shaped space continuous with what you previously outlined (above figure, yellow outline).  Label this as a part of the third ventricle. With another section or two anteriorly, this space will contract and end.  Go back to the AC level.  Above the AC, you may see a small hole, which corresponds to a small part of the third ventricle (toggle back and forth between slides to convince).

<img src="https://lh3.googleusercontent.com/vmJjyCBnyZumXVurOliVzkqw3Tu-vQGT3l6ajTppTIgcRJ2cdRHgQzs-2QvJ-gPt2Fm7L424FOV3" alt="" title="Figure 12: Foramina of Monro">

2. Mid-portion. Now you will work your way to the back of the brain.  Immediately behind (posterior to) the AC level, you will find the foramina of Monro (n.b., foramen is latin for aperture, foramina is the plural and there is one on either side). These apertures are where the lateral connect with the third ventricle.  In the above figure , they are observed lateral to the fornix (purple outlined spaces). Make sure that when you segment the 3rd ventricle, you do not extend into these foramina because they operationally belong to the lateral ventricle segments.  The 3rd ventricle should appear here as a fusiform or cigar-shaped structure (figure above, yellow outline), rising to the fornix (the paired white matter bundles at the top of the yellow outline in the figure above) and relatively invariant in width.  After the level of the foramen of Monro, the ventricle will constrict. Using the paint tool with the intensity range, you will be able to outline the ventricle with one click and then move quickly through the sections. If you are having trouble distinguishing between what is classified as lateral ventricle and what is the third ventricle, note that the third ventricle should be pretty symmetrical. The lateral ventricles should be a mostly continuous shape that reaches towards the third ventricle along the midline. Also note that the third ventricle should be cigar like in appearance in these sections, meaning that any editable sections to the right and left of it are most likely the lateral ventricles.

<img src="https://lh3.googleusercontent.com/eGRZnVVZoDb7le3R7Wny9DquMVaX_nsrN27Dl3tQMD9AC57NM84zQpmm-KzFHjyeflcLi7YcXeYE" alt="" title="TCF">

3. At this point, we need to introduce an additional structure that requires separation from the ventricle. This space, called the transverse cerebral fissure (TCF), is also filled with CSF, and while it is not directly connected to the third ventricle, it shares a border with the third ventricle that is often indistinct.  The TCF (green arrow, above image) will become fairly large as you move further posteriorly, but here it is present along the midline under and between two fiber tracts called the fornices (singular: fornix; above image, immediately above the green arrow).  In actuality, this region contains part of the third ventricle, as well as the TCF. However, ***we cannot resolve the difference***, and given the small size of the third ventricle here, we operationally define this space as belonging exclusively to the TCF and not the third ventricle  We will not define the TCF ***per se***, but it is important to note its presence.

<img src="https://lh3.googleusercontent.com/jsmIb9xb6xhFDLonXWHrAhX0zGJy7Ax1vtV0hQR4wtXHmHgXL6ovLz4_ZXtpa3F0BdAXSGxceUfX" alt="" title="Post 3rd">

4. Posterior portion. More posteriorly, the third ventricle will open up.  At this point, you will observe two round structures underneath the fornix.  These are the internal cerebral veins.  Underneath these structures, by adjusting the brightness/contrast, you should see a membrane that tents up with the apex of the tent up and on the midline.  This is the border between the TCF superiorly and the third ventricle inferiorly.  Label the space below this tent with the paint or the draw tool (e.g., yellow outline in above image).  It helps to toggle to the adjacent brain sections using the arrow keys or the mouse wheel to appreciate this boundary.  
You will notice that after a few sections, the third ventricle breaks up into two components by the introduction of a white matter tract (called the posterior commissure) going across the midline.  Once you identify the posterior commissure, the ventricular space underneath it is now called the cerebral aqueduct (of Sylvius).  This space communicates the CSF of the third ventricle to the fourth ventricle and is considered a component of the fourth ventricle.  We will discuss this in the next section, but for now, make sure you do not include this space in your third ventricle segmentation.  
What to do the with third ventricle above the posterior commissure?  Well, it turns out that the third ventricle sends out two small extensions, one that goes above the posterior commissure as the pineal recess and invaginating the stalk of the pineal gland, and one on top of the pineal gland known as the suprapineal recess.  Both of these recesses will appear as disconnected circles in the coronal sections.  Increase the brightness and use the T2 to help you examine them. Also, employ the mid-sagittal views to show the continuity.  
And finally…  When you have completed your work on coronal sections, switch to the sagittal section series and find the mid-sagittal section.  This should reveal the third ventricle in all of its glory, and this is a good section to identify gaps or holes, as well as to identify jagged edges.  Smooth them out, and proceed in either direction to make sure things look cohesive and connected.  
Make sure you look at the other views to make sure structure has good borders in all dimensions.

## The Fourth Ventricle
Using the paint or draw tool with the previously defined intensity range, outline the cerebral aqueduct on the coronal section (see previous section) and move to the next posterior image. It is useful to start in the coronal plane and then switch to axial once you have completed at least a few segments in the coronal plane.  It is also useful to quickly view the fourth ventricle in a sagittal view before finishing this segmentation.

Keep in mind that one potential issue is the degree to which the spaces between the cerebellar folds are included as ventricle.  Following several of them throughout multiple views will clarify which are connected to the ventricle, and which are not.  Use the axial view to inform your decision, and base your decisions on the shape of the ventricle, as depicted in the 3D image of 3DSlicer and in the lower right portion of the above figure.

The fourth ventricle is a tricky area to segment. It will be most helpful to view the brain in the four-up display mode, so you can see any immediate impact of any changes. Start segmenting in the coronal view, starting with the first appearance of the cerebral aqueduct, which leads into the fourth ventricle. Remember this first appears under the posterior commissure. You may have to edit the intensity range or fill in segments based on the knowledge that the fourth ventricle is a continuous entity. As you go on, the fourth ventricle will gradually become bigger. At some point in the coronal view, the fourth ventricle will begin to flare out.  At this stage and before the cerebellum starts to fill the space, switch to the axial view to segment.  In the axial view, continue to segment.  You will notice that the center of the space will become filled with the cerebellum and the fourth ventricle will look like an upside down U.  As you proceed inferiorly, the sides of the ventricle will shrink in size until the ventricle looks like an extended mustache.  The lateral parts of the mustache will soon connect to the space surrounding the brain.  These holes are the lateral apertures (of Lushka).  Our convention is that when this connection is made, the segmentation ends. You will notice that more medially, the ventricular space continues inferiorly on the dorsal aspect of the medulla - continue to segment until it disappears.

In some brains, the cerebellum fills the fourth ventricle and gets very close to the the walls and even the floor.  When this happens, the partial voluming will preclude labeling, and our convention is to make a connection to illustrate that there is a continuous floor and walls of the fourth ventricle. To this end, use all three viewpoints to generate a structure that is similar to that observed to that observed below (#14).

<img src="https://lh3.googleusercontent.com/4sWJxRa37DdOB1hT1s4d1qoajAkenEYwDtmPBiHqdcBbC81MAkrpzFxm7DVnSDuy-BCOucpzjfAN" alt="enter image description here" title="3rd V Modified from Nieuwenhuys 2008">

### Final comments on Ventricular segmentation

You will notice that in some brains, the initial part of the fourth ventricle or parts of the third ventricle are fairly small and not labeled by the threshold you have selected due to partial voluming of the surrounding structure.  To overcome this, change the threshold so you generate a cohesive segment.  Make sure you change it to the lowest threshold that will give you such a complete structure.  This is also applicable in some brains in which the dorsal part of the lateral ventricle (over the caudate) becomes too thin or compressed to resolve – in the 3D view, this will appear as holes in the structure.  Finally, the connection of the posterior horn with the atrium of the ventricle may be disconnected.  Here, the spaces may not be confluent.  Change the brightness slightly to convince yourself one way or the other, and use the 3D view as you review your work.

## The Nucleus Accumbens
Now that the ventricles are complete, we can start segmenting gray matter structures. We will begin with a structure called the nucleus accumbens.  To segment this area, we need to understand more about the anatomy of two other regions: the caudate and the putamen.  If you examine the lateral ventricle in a section anterior to the foramina of Monro, you will find a gray matter structure adjacent to it on its lateral border – this is the caudate (see figure below).  At thitse anterior end , the caudate is quite large and comprises almost all of the lateral border of the ventricle.  At the most anterior regions of the ventricle, the caudate is the only gray matter structure at the center of the brain (figure below, left hand side).  A bit more posteriorly, a new gray matter structure will appear as a small ovoid and then progressively enlarge.  This structure is the putamen (see below figure).  The putamen is separated from the caudate by a white matter tract called the internal capsule.  In some sections, you may notice that bridges of gray matter extend through the internal capsule to connect the caudate and the putamen.

<img src="https://lh3.googleusercontent.com/UUmesFIG8MecZt3tCOtYyrIiWOzkd8cSdnlUiZxhiP7wL7P_Qpa_7Fq9iBXPR7XX5klGCxFGrBoI" alt="" title="Caudate, Putamen and Internal Capsule">

The caudate and the putamen meet underneath the internal capsule.  This area is a separate region called the nucleus accumbens.  We have to outline it first because its location uses an operational definition based on morphological landmarks, rather than one based on intensity or visible borders.  Segmenting this structure first makes subsequent segmentation of the caudate and putamen much easier.

To start with, select Nucleus Accumbens Left from the segment editor (recall that you will segment on the right side of the image, per radiological conventions).

We now have to adjust the masking threshold to produce an optimal border between the nucleus accumbens and the ventricle.  Find the coronal section in which the anterior commissure crosses the midline (figure below, dashed yellow line).

<img src="https://lh3.googleusercontent.com/Yp4rV91cMxvYuBg_eFBCIh8K-kshiuvoTCuudcjr0p0HCp-ZW5iwUPhbJ4N_edjCDN2xKDv0og_d" alt="" title="Anterior Commissure">

Go to the threshold button, expand the local threshold option, and select ‘Draw’. Make a drawing that includes the caudate and the ventricle (white box in figure above).  This will produce a histogram.  As before, select the first peak and second peak by clicking, holding and dragging.  Under lower, select average, under upper select maximum.  Note the number corresponding to the lower bound (under the threshold range above the histogram) and insert it in your spreadsheet.  This is the threshold value between the ventricular space and the gray matter.  You will use this a few times for different structures. Click on the ‘Use for Masking’ button.

Click on the draw tool under effects (third from left). Scroll down and make sure you select ‘Outside all visible segments’ in ‘Editable Area.’  Check the box next to masking and make sure that the value selected in the histogram above is the lower bound.  The upper bound should be maxed out.

We will now use the draw tool to segment the nucleus accumbens on each side.  Find the first section where the internal capsule / putamen first appears (See below on right side of image).

<img src="https://lh3.googleusercontent.com/5cqeCtP7P3zBwFTSaJhPbMFNdAjlFWpqFZZv28EV57GxsD7xBwSxKTYHB6T4NnEwUL6Wa_LF1eh2" alt="" title="Nucleus Accumbens - ANT">

Click on the inferior and lateral point of the lateral ventricle and draw a straight line to the inferior and medial point of the putamen as indicated by the figure.  Do not click a second time just yet, but notice where the line crosses the internal capsule.  Move the mouse to where this line crosses the internal capsule.  Click and you should have a line that goes from the lateral ventricle to end in the gray matter right before (medial to) the internal capsule (above figure).  Then use multiple clicks (or click and drag) to follow the inferior gray-white border medially and then dorsally to return to the originating point. Then right click to accept it.

The definition by the Center for Morphometric Analysis (CMA)’ at MGH indicates that the nucleus accumbens starts before the putamen and the caudate merge.  You will continue this approach for the next posterior section, and you will notice that the putamen is increasing in size.  The internal capsule will then disconnect from the inferior white matter and the caudate and the putamen will be in continuity (figure below).  When this happens, place your line from the inferior and lateral border of the lateral ventricle to the midpoint of the internal capsule (1).  Then draw a line straight down to the white matter (2). The follow the white/gray matter interface medially back to the origin (3).

<img src="https://lh3.googleusercontent.com/tFnALxUolYpYZAuAhTXWsta18jKaBeiwxNTH_FTbTswWa5ztRoqtsAtCjY_3GWU1zt9iQOyYfWQk" alt="" title="Nucleus Accumbens Post ">

Continue using this approach until two images before the appearance of the anterior commissure, at which point the nucleus accumbens will end.  Keep in mind that as you make your way posteriorly, the coherent white matter on the inferior and medial borders will begin to look a bit more grey.  It will be lighter than the gray matter, but please do not label it. Keep the distance between the brain surface and the label consistent with previous sections.  If in doubt, use the arrows to toggle between images to convince yourself of a consistent medial and inferior border.

After you’ve completed the segmentation, review the axial and sagittal sections and made edits.  The process of segmenting structures in the coronal plane opens the door to have inconsistent ‘stair-like’ borders from section to section.  These discrepancies in the borders are difficult to appreciate (i.e., placing the vertical plane (2 in the figure above) in the coronal series, but will stand out as a jagged border in the axial or sagittal view).

After completion, proceed to Nucleus Accumbens Right.

## The Caudate
Now that you have outlined the nucleus accumbens, you can move on to the caudate.  The caudate is fairly heterogeneous and may contain some voxels that are nearly as light as those found in the internal capsule.  The border between the caudate and the ventricle will be set by the thresholding method with the same value you used for the nucleus accumbens.   Recall that when you segmented the lateral ventricle, the histogram tool was used to determine the border between the white matter and the ventricle.  This threshold was not perfect for the border between the ventricle and the caudate.  This is where we remedy this problem.

In the nucleus accumbens segmentation step, you determined the threshold between it and the ventricle by measuring the border between the caudate (gray matter) and ventricular space.  We will continue to use these values, but we now have to adjust the visible segments so we can overwrite the ventricular border, but not the border of the nucleus accumbens with the caudate. Go to the masking section, and in the Editable area, select ‘Outside all visible segments’.  Then progress up to the segment selection bar and click on the eye next to each lateral ventricle.  The lateral ventricles will disappear.  Make sure that the nucleus accumbens you just segmented is visible.  These operations will allow you to overwrite the ventricular voxels that impinge on the caudate without affecting the nucleus accumbens.

Some people like to start segmenting the caudate from the axial perspective (there are fewer sections and so it goes slightly faster), and then finish the trickier inferior margin in the coronal sections.  Others (most)  prefer to do one take, and start from the anterior part of the caudate, working posteriorly. Either of the aforementioned approaches is acceptable. As you do more segmentations, you will find a method of drawing the caudate that is most efficient and accurate for you.

Whichever way you choose, be aware that the caudate has several parts.  The portion in front of the foramen of Monro is the called the head of the caudate.  It is bounded medially and dorsally by the lateral ventricle, laterally by the internal capsule, and ventrally by its border with the nucleus accumbens.  The image below shows the nucleus accumbens (yellow dashed line) and the caudate (white dashed line).  When you segment, the border with the ventricle will be adjusted automatically by the thresholding, and the border with the nucleus accumbens will be set by exclusion (i.e., it will be a joint border).  The border with the internal capsule is not smooth because the gray matter of the caudate extends into the internal capsule, and you will have to make a judgement call about what to include.  Most people decide to draw a relatively smooth line at the interface and do not include the bridges of gray matter as a rule.

<img src="https://lh3.googleusercontent.com/0czk2AgeW9aaSUi8HLrYmP9nEVXBe6lRxiqsI7fB2azySxoOh4bzlt_IlBfI2fTEtm8xx29wDUVF" alt="" title="Caudate">

When the nucleus accumbens disappears and the anterior commissure (AC) appears, a section similar to that below is observed.

<img src="https://lh3.googleusercontent.com/wZQ84lOkjzJNnTcpp7wy-rER5jD6fLXd29VurgaWFqktQDfPq6Lt7Z0Mj4nZCQ5snqm_DfRXaoOz" alt="enter image description here">

The convention is to extend the caudate inferiorly to the AC since the AC is a relaible and consistent landmark.

Once we move posteriorly to the foramen of Monro, the caudate gets pushed to the lateral and inferior border of the lateral ventricle.  Here it is called the body of the caudate, and it will diminish in size as you proceed posteriorly.  After the foramen of Monro, a large heterogeneous structure called the thalamus comes to dominate the central part of the brain and displaces the caudate dorsally and laterally.  In the figure below, the caudate nuclei are enclosed by white dotted lines.    Note that in some brains, intensities similar to the caudate are observed more superiorly in the region of the head and body of the caudate.  These voxels are unlikely to belong to the caudate, but to a fiber bundle called Muratoff’s bundle (Schmahmann & Pandya, 2007; superior occipitofrontal bundle of Crosby (1962)).  Alternatively, white matter hypointensities may occur in this region.  In both instances, use the axial and horizontal views in conjunction with the cross hair tool to make sure the caudate is correctly assigned.

<img src="https://lh3.googleusercontent.com/2OAP2ym9bWJU-9N5do4u-T0_jdaH3nkUWU-qRnbhAWIrNSVkuCsB9WD0QoeOEmLeYSfzuXM0kTP8" alt="enter image description here">

Notice that the lateral ventricles are typically more flattened at the level of the thalamus (see figure above). When the thalamus disappears at a more posterior stage (see figure below), the ventricle enlarges ventrally as the atrium. What is really happening is that the ventricle curves around the back of the thalamus.  The caudate also wraps around on its way to the temporal lobe, and when the ventricle opens up, you can identify the caudate laterally in the ventricle, and now pointing ventrally (see dotted line in figure below).  Label the caudate as it progresses ventrally, but be careful not to label the similarly intense choroid plexus, which is a bit more medially.  Use the axial view with the crosshairs turned on to make sure of your segmentation.

<img src="https://lh3.googleusercontent.com/JHHd4InilC4xnQM8nQjm1ut3jcLciSvYRtdU-XeKnVZGRkqtQOxdJ7wPEkMhZR-zpZYB2XEiePMe" alt="" title="Posterior Caudate">

At this point, we will stop with the caudate.  It does continue into the temporal horn of the lateral ventricle as the tail (on the roof, no less), but it is too difficult to identify reliably.

In 3D, the caudate should look like a comma, with a head and the tail for which it is named (caudo- Latin, tail).

You’ll notice on your review that the caudate is bit irregular in other dimensions.  It should be smooth where it contacts the ventricle, but it tends to have irregularities when it meets the internal capsule laterally.  This is largely because there are bridges of neurons from the caudate that weave through the internal capsule.  Including some or parts of these bridges creates irregularities, and it is best to smooth out the medial border to exclude these bridges as a matter of definition.  The other portion of the caudate that is a bit tricky is the tail.  You’ll want to review the end of the body and the tail to insure consistency in the border, but you may find that there is a bit of a contraction of the structure of the caudate before it widens and proceeds ventrally.  The tail of caudate in the atrium is clear, but must be carefully distinguished from choroid plexus.  Using all views with the crosshairs helps with this.

When you are finished, turn on the ventricle and review the caudate in its entirety.  Be sure to turn off the visualization of structures on one side so you can inspect the medial caudate border.  Something to watch out for, especially in the region of the posterior thalamus, are discontinuities in the segmentation.  These will appear as ‘holes’ in the caudate.  These holes are highly unlikely to be real, but instead reflect partial voluming or inaccurate segmentations and should therefore be remedied.

## The Putamen
The putamen is the next structure to segment.  This is a structure present laterally to the caduate and internal capsule and has a similar intensity to the caudate.  You may begin with the same intensity range you used to segment the caudate nucleus, but the larger number of myelinated fibers that randomly pass through the putamen (particularly posterior to the foramen of Monro) makes this approach somewhat ineffective.  For this region, it is best to use the draw tool without any masking.  The putamen is almost as long as the caudate.  The putamen is quite easy to visualize, but even so, there are several points detailed below where you should pay special attention.

Return the ‘Editable area’ under masking to ‘Outside all segments.’  Select the coronal view and segment from anterior to posterior.

In the most anterior portion of the putamen (see figure below) observe that the putamen is very small on the right side of the image.  Anterior to this section, the putamen may be comprised of isolated islands embedded within white matter.  When those islands become coherent, this is when you will want to begin segmenting.

<img src="https://lh3.googleusercontent.com/i9eNcGve7Ees6NLFbVQzlV7FqzCJq7S-p05GDedx4nIwf3ogfGjwsfokCuyy7dR0IeENf97tfC9f" alt="" title="ANT Putamen">

As you progress posteriorly, you’ll notice that the internal capsule forms the medial border, and a smaller white matter segment (the external capsule) will form the lateral border.  Lateral to the external capsule is a thin gray matter structure called the claustrum (outlined in red in figure below). Do not segment the claustrum and make sure that the lateral border of the putamen does not extend into the external capsule or the claustrum.

<img src="https://lh3.googleusercontent.com/5a2pYAWDV09DOSx1Aos_1XX42kdYxLAJ12nUMtFsjBMvVxQEZ9avGqM4ur8Rp7NZ0McdbEdyDQXY" alt="" title="mid ant putamen">

The ventral border of the putamen should be consistent with the ventral border of the nucleus accumbens.  As you reach the anterior commissure, a nucleus will appear on the lateral border of the internal capsule and will push the putamen laterally.   This nucleus is the globus pallidus (GP, in figure below), and it will ride on top of the anterior commissure (in white).

<img src="https://lh3.googleusercontent.com/foGyfS6LxlBUcarXWnYGZilpiSZnkNJVNCoRtvouVGnikfL8VEnr5UDM6q8jtsXJnhsMKzqXB5M0" alt="" title="Putamen with GP">

Make sure your putamen segmentation does not impinge on the globus pallidus, nor under it.  You may be tempted to segment under the anterior commissure, but please resist - this is a different brain region.

After you move posteriorly and the anterior commissure disappears, the putamen will be pushed laterally by the enlargement of the globus pallidus (as in figure above).   The ventral aspect of the putamen is ofttimes marked by large black holes.  On the left side of the image in the above figure these holes are found on the lateral and inferior border of the putamen adjacent to the external capsule.  These are branches of the middle cerebral artery, and should not be labeled as putamen.  You can actively avoid these using the draw tool, or assign the threshold to automatically exclude.

As you continually posteriorly, you’ll notice that the anterior commissure is progressing laterally into the temporal lobe of the cerebral cortex.  By moving anteriorly and posteriorly in the coronal views, you can identify the anterior commissure anteriorly.  At more posterior levels, pieces of it are observed progressing laterally and inferiorly.  In the figure below, the anterior commissure pieces are labeled by a white dashed bounding line.  After it passes under the putamen, the anterior commissure will form a boundary between it and a composite gray matter structure (mostly the amygdala).

<img src="https://lh3.googleusercontent.com/V51Q7t_TgqgNcIlvD8q5Jmkp2kmcfxTfMHhr8ELXfATaFggOdGILgXLNHZhvrf8zJg0qj-Io7FK9" alt="" title="Post Putamen">

At more posterior levels, the anterior commissure extends even more laterally and will enter the temporal lobe white matter.  At this point, the putamen will extend ventrally into a taper (see image below).   This is referred to as the tail of the putamen or as the ventral putamen.  In the figure below, the tail of the putamen is nicely encapsulated by white matter inferomedially and the border is clear on the right side of the image (dashed line)  On the left hand side of the image, this border is not clear because the putamen is merging with other structures (e.g., amgydalostriate transition area, amygdalar nuclei, etc).  A straightforward way to segment is to leave this transition area for last.  Segment the clear anterior regions of the putamen and the clear regions posterior to the transition area (to the end of the putamen).  Then progress slice by slice through the transition area using the borders in the adjacent sections to guide you.

<img src="https://lh3.googleusercontent.com/b1-weOe_oG9bqxbcTp1gJ9H5lFacMsg-6y4BjKXs9yw2fIRvcxaPJrRhBKpguu57FdngsDzCWs6O" alt="" title="Ventral Putamen">

Supplement this approach by examining the putamen in the axial and sagittal views in conjunction with the crosshair.

## The Globus Pallidus

The globus pallidus (GP) is a structure located between the putamen and the internal capsule. It is roughly triangular in shape when observed in the coronal plane, and is nicely viewed in the sections posterior to the anterior commissure.  Since there is a great deal of white matter traveling through the globus pallidus, it can be difficult to pick out which  portions of the white matter belong to the globus pallidus and which belong to the internal capsule. To begin, pick several sections around the anterior commissure where the globus pallidus is very clear. Then segment it by applying the paint or draw tool without using the intensity range.

The globus pallidus is nicely distinguishable at the level of the anterior commissure - this is a good place to start (see upper image in the figure below, white dashed outline).  From here, follow it forward it until the globus pallidus shrinks and disappears.

The figure below also exhibits a unique feature of the globus pallidus.  Unlike most brain structures, the neurons of the globus pallidus take up iron and are therefore a bit darker on the T2 weighted image.  The upper image in the figure below is a T1 image with the globus pallidus outlined.  These same outlines were applied to the same slice from a T2 image. By comparing the two images, you can see that the lateral border of the globus pallidus with the putamen is remarkable sharp.  However, it is also easy to observe that the globus pallidus on the T2 is difficult to distinguish from the white matter of the anterior commissure or the internal capsule.  The T2 may help you figure out some aspects of the structure, but use it to assist the segmentation on the T1 images rather than explicitly demarcating the borders.  Finally, keep in mind that other structures adjacent to the globus pallidus take up iron, so use the T2 images carefully.

<img src="https://lh3.googleusercontent.com/HnuiVcafbhYF_Vepu6wHuyVz0RIKWgcKyJYTvl9paMlH-UP4fl7RgSLAvM0KZ2-J_1Mbf-RXyqh8" alt="" title="GP T1 T2" width="500" height="1052">

It also helps in this instance to adjust the contrast / brightness.  But please remember to return the values when you are complete.

As you segment the globus pallidus posterior to the anterior commissure, it will become more difficult to determine the borders.  As you go, recall:

- The lateral border of the globus pallidus is shared with the putamen, and there should not be unlabeled voxels between.
- In anterior sections, the inferior border of the globus pallidus is the anterior commissure.  Make sure the segmentation of the globus pallidus does not  include the anterior commissure.

At the level of the mammillary bodies, the borders of the globus pallidus become fairly difficult to discern.  A good approach is to switch to the axial view and use the segmentations you have completed at more anterior levels to guide you in more posterior levels.  In the axial view, the globus pallidus will come to a taper posteriorly and will be within the putamen.  The globus pallidus will not extend as far posteriorly as the putamen.

Two final notes.  First, the globus pallidus is comprised of two parts (external and internal).  These are nicely viewed in the middle coronal sections through the structure.  The last part is that the most posterior limit of the globus pallidus is quite difficult.  The T2 weighted axial images are particularly helpful for this.  In the image below, note the putamen (dashed line) contains lighter voxels, whereas the more medial wedge (medial border with a solid line) is much darker.  This is the globus pallidus and the unlabeled left side of the image shows well its posterior tapering within the putamen.  Note also that the anterior part of the GP is indistinguishable from the internal capsule.

<img src="https://lh3.googleusercontent.com/98RI78aHvMpZ1FzzrvHyxtGE61EKdXNFdcal15yS4FgmhfJjeFa5IrJg3_J1Bcn_dvHOGGeAsbxQ" alt="" title="T2 Axial GP">

When reviewing the globus pallidus, make sure the ‘fill’ option is turned off so you can get a good idea of the contours.  Concentrate on the posterior tail, and the inferior border, particularly after the anterior commissure.

## Brainstem

The brainstem is a collection of regions that includes the midbrain, the pons, and the medulla.  This structure is operationally defined by two planes that you will establish on a midsagittal image.  This will produce a fiducial marker in the coronal planes that you will use to define the boundaries of the brainstem.  This is a bit tough to get your head around, so read on and all will become clear.

When discussing the brainstem, slightly different terms are used. In the other structures, the terms anterior and posterior are used to denote front and back of the body.  With the brainstem, orientation along its long axis can be referred to as rostral (towards the brain) and caudal (towards the spinal cord).  This is necessary because the long axis of the brainstem is not the same as the long axis of the forebrain.

Find the midsagittal plane.  It will look something like the figure below.

<img src="https://lh3.googleusercontent.com/VMV51kGoyjLSKOVzu2ZUR0EZ1192Q8SBOwVvXfEVknTLhHmYw1v5ofpnmeCgArJOq94dVNRxN_O9" alt="" title="BS Sag">

The first plane separates the brainstem from the thalamus and a region we will segment larger called the ventral diencephalon (VDC).   Identify the posterior commissure.  In the figure above, the posterior commissure is the small white structure to the right of the white asterisk.  Using the draw tool, draw a line from the posterior part of the posterior commissure to the prepontine recess on the ventral aspect of the brainstem (follow the yellow dotted line in the direction indicated by the red arrow and the encircled number 1).  It is useful to set the intensity bounds higher than the margin you set for segmenting CSF so you automatically select brain matter.  Move inferiorly around the anteroventral aspect of the brainstem following the red #2 arrow.  Your line should approximate the yellow dotted line and exclude blood vessels (the really bright tube ventral to the brainstem.  Keep going until you see a divot in the brainstem (where the line ends in the figure above).  From here, make a second planar line through the brainstem.  This line will end in a depression in the floor of the fourth ventricle - a depression called the obex.  You’ll then make your way through the fourth ventricle, dip up in front of the cerebellum (and in back of the bump, and then go back to the origin of the line.

Go to the coronal view, at approximately the coronal level below.  Notice that there is a magenta vertical line bisecting what appears to be a double bubble of gray matter.  This structure is a cut through an island of the most anterior part of the brainstem and the magenta line is the representation of the brainstem that was just done on one sagittal section.  To put it slightly differently, since you drew an outline in the sagittal plane, viewing the brain in the orthogonal coronal plane will represent that plane by a line and the outlining on the sagittal section allows for the subsequent identification of the brainstem on the coronal sections.  Here the brainstem is observed as isolated, but in more posterior portions it will connect to the brain. At this stage, segment the brainstem similar to the dashed white line below.  Keep in mind that nerves and blood vessels are closely associated with the brainstem, and these structures should not be included.

<img src="https://lh3.googleusercontent.com/eqXYd4R_7dpDPxtrHVdp1SNvxjfdO6nLnx1yzSxWU5TtnKYMH546kWkz4-Snj31sZ8OzGepxSpMO" alt="" title="Brainstem ant">

As the sections proceed posteriorly (and caudally in reference to the brainstem), the labeled brainstem becomes larger and connects to the brain. Your line around the brainstem should be consistent with the previous outline, and should separate the thumb-like structures from the contour of the brain proper, as indicated below with the dashed line.

<img src="https://lh3.googleusercontent.com/qZS7KTC2CKTjVl1eDa-JyTSM8bhz9RYwyK3SauowNj_bU1ul2CegoZwL7Twvt2oLp2Z4pycEBT_F" alt="" title="Brainstem 2">

As you proceed even further posteriorly, the line will get longer.  When the brainstem initially connects to the rest of the brain as in the above figure, the line will connect the ventral aspect of the brainstem with a space called the interpeduncular fossa.  With more posterior sections, this fossa will disappear (figure below), and the vertical marking line will be observed to end in the substance of the brain. In sections such as this, use the draw tool to draw a horizontal line from the dorsal aspect of the marking line, as indicated by the dashed white line. This will demarcate the brainstem.

<img src="https://lh3.googleusercontent.com/ltqKhGTuv1AQBG9WzIHNy9TwAmpoNY0wJiUYFyW0fmnWvFz1uTzqDdIv7aFYWUwgWYtnZN_zaeSe" alt="" title="Brainstem 3">

Pause at this section, and scroll posteriorly to observe the middle cerebellar peduncles (MCP) as lateral bumps on the brainstem, as in the figure below. The MCPs are excluded from the brainstem segmentation per se and will be included in the cerebellar parcellation.

<img src="https://lh3.googleusercontent.com/jlKMOsJS-K26hgEaWh3vha30US0gmryjreoiTqsDSVk2_h1J3nKx7JB8AraPc0cFhJyXGrp0ZpMw" alt="" title="Brainstem 5">

Find a section where you can clearly view the peduncles, as the above section.   Using the draw tool, draw a vertical line through each one of the peduncles that is parallel to this vertical fiducial brainstem line.  Start with the upper border of the brainstem with the MCP and draw toward the bottom of the screen.  Continue using the draw tool to follow the contour of the brainstem to the other side, then draw another vertical line parallel to the fiducial line (dashed white line).  This should exclude the MCPs on each side. Also notice that there is a hole (the cerebral aqueduct) in the middle of the brainstem.  In your segmentations this will be labeled as ‘fourth ventricle’ and is labeled here with a dashed blue outline.
At point, you have segmented the rostral sections of the brainstem, and jumped caudally to segment the brainstem at the level of the MCPs.  Now you will close the gap.  Move one section anteriorly in the coronal plane from the brainstem image you just segmented.  Segment the brainstem just as you did for the previous section.  As you move in the anterior direction, the MCPs will decrease in size (see image below).  To the best of your ability, keep the vertical lines between the brainstem and the MCPs constant in location.

<img src="https://lh3.googleusercontent.com/5d1ujnJWIbTKHfJ8ityCw2Y5EEHWL3b3bqMqxP5qk6n7ByYa2ylhqUG66lwqwCIpeFV4jiiaqYi-" alt="" title="Brainstem 4">

In the image below, notice that the dashed lines exclude the smaller MCPs laterally.  Also notice that the fiducial line has now gone above the ventricular space of the brainstem (labeled the fourth ventricle).  Above this, there is a very small horizontal contour, which then on both the left and right, gives way to an oblique line that extends inferiorly and laterally until it joins the external contour of the brainstem.  This line is important because it excludes diencephalic structures such as the pretectum and the medial geniculate body of the thalamus.
Once you have reached the previous brainstem segments and closed the gap, you will have to finish the brainstem caudal to the MCPs.  Go back to the first MCP section you segmented and proceed posteriorly in the coronal plane.  As you did before, use parallel lines through the MCPs to separate them from the brainstem.  Again, try to be constant in placing the positions of the vertical lines that separate the MCP from the brainstem.  You will notice that the fourth ventricle has increased in size (blue dashed line in image below).

<img src="https://lh3.googleusercontent.com/hwUSD1EYWDD5O5NpVqttaZaczKjyOuMxtyKr-oz7NzrfwnL_mjK9TRm5ikpUdaHEuB6-49bOfwsX" alt="" title="Brainstem 6">

Also notice two little, joined bumps (the inferior colliculi) at the top of the fourth ventricle.  As you proceed posteriorly, these two bumps will become disconnected from the brainstem, but you should still outline them.  In the figure above, they are joined to the rest of the brainstem, but just barely.  At this stage, the vertical brainstem fiducial line is starting to get shorter at its inferior aspect, and ends within the substance of the brainstem.  When it does disconnect from the surface of the brainstem, draw a horizontal line at the base to separate the brainstem. This means that you are reaching the caudal extent of the brainstem.
When you are finished with the coronal sections, examine the sagittal sections.  As you processed off the midline, you will find that the floor of the fourth ventricle may not be included.  Please include it on either side and proceed laterally.  As you do so, you may find that the lateral borders are jagged as there are small inconsistencies in the exact placement of the bounding lines that separate the brainstem from the MCPs.  Please clean these up.

## The Thalamus

As indicated above, the thalamus is a large egg-shaped structure immediately posterior to the foramen of Monro.  There are two thalami and they are separated by the third ventricle. Due to the small size of the ventricle and partial voluming effects between gray matter and CSF, this separation is not always apparent and it appears that the left and right thalamus merge on the midline.  In some instances, this is accurate - a proportion of humans have a small piece of gray matter that connects the two thalami.  Many other vertebrates have this connection, which is known as the massa intermedia. However, the partial voluming doesn’t allow for this distinction, so operationally we divide the left and right thalami on the midline.

The thalamus is separated from the hypothalamus by a groove called the hypothalamic sulcus.  This is a critical landmark in defining the thalamus.  The image below is a sagittal image that is near the midline.  The border of the thalamus is indicated by a white dashed line. Under the thalamus and anteriorly is the hypothalamus (indicated by an ‘H’).  Between the two structures is a black space, filled in the image by a yellow dashed line. This is the hypothalamic sulcus, a groove within the third ventricle, and it will be indicated on subsequent coronal sections by a yellow arrow.

<img src="https://lh3.googleusercontent.com/82JA6IruKgY57XnDnPGjJky993Nka7YVfL6KcGa8Rqep9TAlU8wHRFD-3uvET43a8LJ6m8pWx7Fu" alt="" title="Thalamus MS">

The coronal section below is taken from the middle of the thalamus.  The hypothalamic sulcus is at the tip of the yellow arrow and is seen as a  lateral extension of the third ventricle. A line extending laterally from this sulcus and then following the tips of the white arrows superiorly constitutes the inferior and lateral borders of the thalamus.

<img src="https://lh3.googleusercontent.com/mkp4ty0QHfs9OdzzuGQSepTqI20bTto-jOH75Us6-Jzm6uLGS8TfqiyGLsPSlrBYErRq5uJ-K_6J" alt="" title="Mid Thalamus">

In the above view, the borders of the thalamus are somewhat clear.  You may also be able to divine the medial and lateral compartments based on density. This is not always going to be the case.  Depending on the brain, you may find you have to adjust the brightness/contrast settings to observe the borders.

In general, the most difficult portion of the thalamus is the lateral border.  This is because the lateral aspect contains many of the axons (white matter) that enter and leave the thalamus.  This admixture of white and gray matter creates a poorly resolved boundary.  A good approach is to identify a border that is very clear at the level of the mid thalamus (e.g., above image), and then move forward and back to adjacent sections.  This border will move very little from section to section.  The inferior border of the thalamus will always begin as a horizontal line that begins at the hypothalamic sulcus and the medial border will be along the third ventricle.

In a more anterior section (below), the hypothalamic sulcus still marks the inferior and medial border.  From here, the border goes laterally, then obliquely superior to lie under the caudate.

<img src="https://lh3.googleusercontent.com/8HNL5sWQvi8TqB5NByC538Ic3xHYDk60HgJVUaIPuYlHU2ilmLwkPLLdrGQZlx09M_H8M2WHop5D" alt="" title="Ant thalamus">

More anteriorly, the thalamus shrinks, but the hypothalamic sulcus (yellow arrow, below) is still the inferior border.  The sagittal view helps to evaluate whether you have gone far enough anteriorly.

<img src="https://lh3.googleusercontent.com/c9wSpPsUuAYknXygCnavWtBynp2bubGev3_OWyI5_GqmRR1ixo98RmLGk03lKfWzn9u5JzD5SOJ4" alt="" title="Even more anterior thalamus">

Once you are comfortable with the middle and anterior thalamic levels, turn your attention to posterior sections (below).  In this section, notice that the third ventricle is opening up superiorly.  In this section, notice that the hypothalamic suclus (yellow arrow) guides the placement of the inferior aspect of the thalamus and the inferior border of the thalamus is slightly flattened.

<img src="https://lh3.googleusercontent.com/6MlSsBYAbvYLF5OERrFbO_076FNxa111pTnG1sdG1UomWvv6QuEOWRB7Z6jIukOPdbv8A4JHFKuP" alt="" title="Mid Post Thalamus">

It is in sections like the one above that the lateral border is particularly difficult. You can use the T2 image set, changing the brightness, the 4-up viewpoints, and the continuity with previous (more anterior sections) to help.

As you progress more posteriorly, you will observe the space between the thalami open up.  The remnants of the hypothalamic sulcus are still present, and the thalamus maintains its general position while diminishing in size.  At this point, there are two small bumps on the inferior aspect of each thalamus.  These are the geniculate nuclei - the medial (M) and the lateral (L) geniculate nuclei.  Notice they are not within the dotted line of the thalamus.  The CMA conventions place these regions into a composite segmentation called the ventral diencephalic area and exclude them from the thalamus per se. It is important to understand what they look like at this level.

<img src="https://lh3.googleusercontent.com/2pNz7x183Bj-IowA8gJobU4VNlDRvxuk9AnHx286qUcZyllWP1w-SrJDD1m8pn7tKYTn7egwVGrK" alt="" title="posterior thalamus">

More posteriorly, the thalamus will become disconnected from the brainstem (image below).  At this level, notice that the thalamus extend inferiorly, and there are no geniculate nuclei.  Also notice that the lateral aspect of the thalamus is difficult to identify as white matter enters the lateral aspects.

<img src="https://lh3.googleusercontent.com/ADYLJogvqUPDxKihN-mAqYR4HT12aj__D8LcvOxilSNcBUYzE-cGerMoq4PddzhfR8A7PKS-AUYC" alt="" title="Posterior end of thalamus">

The thalamus is not particularly easy. Here are some pointers.

- The T2 image set may come in handy in this situation. Remain mindful that the T1 and T2 sets should be used interchangeably to determine the optimal border.  Also remember that the T2 images will have sections where the white matter may have a similar intensity to that of the gray matter.  It is best to start with a mid-thalamic section in which the lateral border is very clear.  Outline the thalamus, and then move anterior or posterior, doing the same. Frequently refer back to the previously labeled gradient, as well as between image sets to ensure you have correctly identified and outlined the border.  It is also useful to examine the axial view to further check your work.
- Don’t be afraid to ask for help.  The first time through, take some time to struggle, but only to a healthy and reasonable extent.  For all structures, and particularly for this one, the more you do, the better you will get.
- Use the sagittal sections and the axial sections to your advantage, particularly in evaluating the anterior part of the thalamus, which is a bit tricky to appreciate on the coronals.  Select the sagittal series and move from the midline laterally, paying attention to the anterior border.

## The Ventral Diencephalic (VDC) Region

This region includes a number of structures in the ventral diencephalon, including the hypothalamus, subthalamus, some thalamic nuclei mentioned above (e.g., the lateral geniculate nucleus (LGN), white matter structures, and some anterior midbrain structures. In many respects, this is a catch-all area because of an inability to reliably distinguish the component brain areas. The superior border of this area is the hypothalamic sulcus, which separates the VDC from the thalamus.  This border indicates that for most of this segment, much of the border of the VDC will be the same as the inferior border of the thalamus. This will not be the case for the very front and the very back of the VDC.

Start in the section immediately posterior to the anterior commissure.  At this level, the thalamus has yet to appear and the hypothalamic sulcus is usually not yet present.

<img src="https://lh3.googleusercontent.com/AS5EGtb6IzN7C6oWSiOPhedH_rHwmnWpR-wdu7VBIfKkIIW9lWDXiPIRfq2tLsbSs0H4gSJVw2O9" alt="" title="Ant Ant Ant VDC">

If there is no hypothalamic sulcus, start along the midline under the white matter of the fornix (the white matter tract right above the red dashed line).  Follow the third ventricle to the base of the brain, crossing the ventral aspect.  Go laterally, and follow the brain surface.  You’ll notice a large white ovoid structure (the optic tract, white arrow).  Include this and consider the lateral aspect of the optic tract as the border of this region.  Once at the lateral aspect of the optic tract, draw a line dorsally and medially (making sure you don’t hit the globus pallidus you previously segmented), and return to the origin of your line.

As you progress posteriorly, the thalamus will appear and enlarge (white dashed line, same outline and image as in the thalamus section) and the optic tract will move laterally.  Use the optic tract as the lateral border as you did previously.

<img src="https://lh3.googleusercontent.com/7dAoC1q0cg-jIMsExbBu00oDvVsSYWnXmbSJxti669QSZeD6Bw6QH5NqSq4pfn6QKziIQLQtGm24" alt="" title="Ant VDC">

Make sure that you don’t overwrite the thalamus as you segment the VDC; the two should share a border.  With that in mind, make sure that the lateral VDC border does not touch the globus pallidus.  You will want to extend the VDC to be dorsal to the lateral aspect of the optic tract.    Keep in mind that the lateral aspect of the optic tract will be the landmark you will use for every section.  Once the optic tract disappears, then its target (the LGN, see the section on the thalamus above) will appear in the same location (see below), and you will use that to determine the lateral aspect of the VDC.  That won’t happen until the posterior aspect of the thalamus, and for now, just keep following the VDC posteriorly.  As the thalamus expands (below), keep the joint border between it and the VDC as the hypothalamic sulcus, and extend the line laterally to the optic tract.

<img src="https://lh3.googleusercontent.com/S-Nipaap0O4813Nuk5lD8Ez_ROfBRtUCpkUctBPO-MlCZwqhukGDJOLQ1NoHsuwV-OjRcZav6HBt" alt="" title="ant vdc">

As you progress even more posteriorly, the optic tract will get a little more difficult to distinguish; it will flatten and may in fact divide slightly (white arrow in image below).  Continue to use it as the lateral border of the VDC segmentation, but you will have to follow it carefully from the previous sections.   In these locations, the border between the thalamus and VDC is a horizontal line starting from the hypothalamic sulcus.

<img src="https://lh3.googleusercontent.com/zU_SVE2m8eoK9RUq2fgYtgKHeNyUBNhob7QrDA7GZhc16KSLEueABe2Btx2hDUlD0LLcjmp1SHJw" alt="" title="VDC MID">

The VDC will shrink considerably and will come to be interposed between the thalamus (white dashed line) and the brainstem (blue dashed line, image below).

<img src="https://lh3.googleusercontent.com/6Zh0Lh4Xuzh5bZm-12e_J4pWEnc-O7r3Rkz8IHhQShniyR0ySo7-LXq9q3eZFjqI2MWAOcRGBXiT" alt="" title="VDC Posterior">

Here the VDC includes the medial geniculate nucleus of the thalamus (M) and the lateral geniculate nucleus of the thalamus (L).  It is important to be able to recognize the lateral geniculate, so before you segment, move to adjacent anterior and posterior sections  for comparison until you feel comfortable with its location.  The VDC at this level will also include a structure called the pretectum, which is between the medial aspect of the thalamus and the brainstem.

Slightly more posterior to the previous section, a structure will appear on the midline called the habenula (image below).  This is slightly intense due to its associate with a white matter tract.  The habenula is diencephalic, but not part of the thalamic region previously segmented.  Instead, it belongs to the VDC, and the borders are correspondingly raised to include it.  Also notice on the image below that the posterior commissure, another structure of diencephalic origin, is cut in half and included in the VDC.  Finally, note that the inferior border of the VDC is horizontal at this stage, reflecting the dorsal fiducial line of the brainstem as previously segmented.

<img src="https://lh3.googleusercontent.com/Jd_CfUT25RCCAWqdHafWjNP3SM4PmqtRrDYB6RrxGGdUvvfutEUJBSng66q5gp3i5eTcvcZeddaM" alt="" title="post post VDC">

The very end of the VDC often adopts unusual shapes as the thalamus and the brainstem approach each other.  The lateral geniculate nucleus (L, above) occasionally persists even in the absence of a connection to the middle of the brain.  This is an additional reason to be sure of its position and extent.

## The Hippocampus
The hippocampus is a gorgeous structure located in the medial aspect of the temporal lobe. It is bordered by the white matter of the temporal lobe and by the inferior horn of the lateral ventricle.  It is somewhat difficult to conceptualize on coronal sections, so parasagittal sections are optimal for initially viewing it.  A nice way to think of the hippocampus is that it bulges into the inferior horn of the lateral ventricle.   In the parasagittal view below, the inferior horn is the dark structure outlined by the white dashed line, and the hippocampus impinges on it.  Notice that the hippocampus is surrounded by white matter (axons that will come to form the fornix).

<img src="https://lh3.googleusercontent.com/Q4e1yARuWL-A7f0YEkbgALxHsSwsHGZgfkEmX4aJy2ImRb_8DFkcEdfTHjYOWXEg9Kw1d7h0c8li" alt="" title="Inferior Horn and Hippocampus">

Return to a coronal view and first look at the posterior portion of the hippocampus in a section similar to that below.

<img src="https://lh3.googleusercontent.com/gLnqpQ8qvDhxJAx3K_scd6K5x378alW0h7vmf0ZH-Wi3rz2mGfeZ1oy1GFEmCI9EskG4mg3VSY9c" alt="" title="Post Post HPC">

In the previous sagittal section, we observed that the hippocampus bulged into the lateral ventricle and here we can observe this relationship.  The hippocampus is denoted by the dashed yellow line, and it intrudes into the atrium of the lateral ventricle.  Notice that it is adjacent to the choroid plexus, which has a very similar intensity.  However, on the left hand side of the image, notice something very important: the hippocampus is surrounded by a white matter envelope that separates it from the ventricle and from the choroid plexus.

In a more anterior section (see below), observe that the hippocampus has changed its position.  It still bulges into the atrium of the lateral ventricle, but now the hippocampus extends medially to the surface of the brain.  In subsequent anterior sections, the hippocampus will be forced inferiorly by the thalamus and will be in the medial aspect of the temporal lobe.

<img src="https://lh3.googleusercontent.com/ZetLHxM9YaTdhAv7ma-PGVVbcgk-6s_ZA_2PSCd4soTpCN5rQa9T8f_uRrgTgwcOZekL-ztwVZbX" alt="" title="HPC posterior">

As we progress anteriorly, the inferior displacement of the hippocampus by the thalamus is evident (see image below).

<img src="https://lh3.googleusercontent.com/QYHoBdHPozErq2Vi_j5Bufx7eMbCwDUU7hg7kzrL29NdXwL1Juc1pkGi-0s603UgLkROxiROMgXN" alt="" title="Mid Post HPC">

Notice on the right hand side of the image that the shape of the hippocampus is different than previously observed.  Here it has a lateral bulge, which then tapers medially.  The hippocampus on the right hand side is perhaps a bit more typical in that it has a larger lateral bulge, but both taper medially.

If you look carefully, the medial taper of the hippocampus continues inferiorly and is continuous with the cerebral cortex that goes inferiorly and undulates on the brain surface.  This continuity reflects that the hippocampus is actually a three-layered cerebral cortex occasionally termed archicortex, and the medial bulge represents a curve in the contour of the cortex as it ends.  From a practical point of view, where should the hippocampus end and the cerebral cortex proper begin?  The medial taper indicated above is a transition cortex that includes cortex called the subiculum and presubiculum (among other names).  These cortices are often included with the hippcampus in an overarching rubric called the hippocampal formation.  So, to be clear, we are segmenting the hippocampal formation per se.  When you segment the hippocampus at this level, the boundary goes to the midline, as indicated above.
There are two other features of the image above that are worth noting.  The first is the position of the fornix.  You are familiar with the fornix as the roughly mustache-shaped structure that hangs down from the medial aspect of the corpus callosum.  However, it originated from the hippocampus, and you can see the white matter of the fornix displayed at the tip of the arrows on both sides.

The inferior horn of the lateral ventricle is also illustrated here as a green dashed line on the left hand side of the image. Notice that it ends immediately laterally to the fornix.  Another way to put this relationship is that the fornix is the medial border of the inferior horn of the lateral ventricle, as explained more below in the section on the inferior horn.

In a more anterior section of the brain, we can observe that the hippocampus has descended even more. Its medial border is adjacent to the anterior part of the brainstem.  The inferior horn of the lateral ventricle is obvious and located laterally and superiorly.  The fornix is not obvious here because its component axons have not been constituted into a discrete bundle.  At this level, gray matter is appearing superior to the inferior horn of the lateral ventricle.  The left side of the image is a bit more posterior than the right side of the image and here we see gray matter from the hippocampus extend medially.  It then and then curves around the medial lip of the inferior horn of the lateral ventricle to form a thin slip of gray matter above the inferior horn of the lateral ventricle.  On the right side of the image, we see the same relationship, but we observe that the thin slip above the inferior horn of the lateral ventricle has gotten thicker. This slip is the amygdala, and it is just starting in earnest at this level, and will grow with more anterior sections.

<img src="https://lh3.googleusercontent.com/sScJkiKYSL42Y_pyzisGS7wI_w8jL8LyW9amuyFnQIIfvOTLpRQuG2r6qrJW-zQS48BwZtfM1yoJ" alt="" title="HPC Mid Ant">

For this level and at more anterior levels, a line extending medially from the medial tip of the inferior horn of the lateral ventricle serves as the superior border of the hippocampus.  It will also be the inferior border of the amygdala, as will be detailed below.
In this and more anterior sections, observe that the hippocampus shrinks in size, but the white matter border between it and the ventricle is maintained.  In more anterior sections, the amygdala will increase in size and the inferior horn of the lateral ventricle will disappear and/or move laterally.  When this occurs, the amygdala will be in contact with the hippocampus, and the hippocampus will be distinguished from the amygdala by the white matter surrounding the hippocampus.  In the section below, the most anterior tip of the hippocampus on the left side of the image is observed as a thin slip of gray matter surrounded by the white matter border (tips of the yellow arrows).  Above and laterally to this, the amygdala (A) is present as a blob of gray matter.   Notice that on the right side of the image, which is a bit more anterior than the left side, the hippocampal tip has disappeared and the amgydala (A) is the only structure present.

<img src="https://lh3.googleusercontent.com/c2dRt6eccBE9eaVhKnjxU2S7HTxI-Zoc2EBWgqFRMTdxczbAR_UED9-5hHUimbn53jdXTyOWsr7R" alt="" title="Ant HPC">

Some folks like to start posteriorly and move anteriorly, as we have done in this guide. Others prefer to identify the anterior tip of the hippocampus and move posteriorly. Whatever the approach, make sure you evaluate the sagittal and axial views to make sure the borders are correct.

## Inferior Horn of the Lateral Ventricle

The inferior horn is an inferior extension of the lateral ventricle.  In this segmentation scheme, it is a separate segmentation unit, but continuous with the lateral ventricle as detailed above.  How then is the division set up in a consistent way?
I’m glad you asked.  Let’s return to the atrium of the lateral ventricle, as (re-) shown below.

<img src="https://lh3.googleusercontent.com/45wAwJKBk3NyjeNkXyVNObDYEhBN5_OxnD77BPSB0ufOBOBJMG1jTgw_QrYFfxlVHifmkl8BJ3ZY" alt="" title="Atrium of Lateral Ventricle">

In the previous segmentation, both of the ventricular spaces here were classified as ‘lateral ventricle.’  Anterior to this section, recall that the thalamus appears, and pushes the hippocampus inferiorly.  In doing so, it separates the spaces into two separate, disconnected spaces.  In the first section it does so, the inferior space is now segmented as the inferior horn of the lateral ventricle (ILV).  See the below image.

<img src="https://lh3.googleusercontent.com/zuPqGT_btMgS839z93SaUXss_QzG-ntOsQBmFQFLinyxqaLN6Kv4C6-CvzzyZZ9aO3S3_o4vvvmA" alt="" title="ILV post">

In this image, the lateral ventricles (LV) are superior, and the ILVs are inferior (green dashed lines). The hippocampus is where we previously observed it, and the thalamus has appeared on either side.  At this point, however, white matter is connecting the thalamus to the cerebral white matter laterally and disconnecting (from this perspective) the ILV from the ventricle.

A careful view of the above image reveals why the ILV is a difficult structure to segment.  The ILV is often very small and is therefore subject to the effect of partial voluming that was previously discussed.  Moreover, the choroid plexus is present in the ILV, which obscures it further.  Both ILVs (dashed green lines) don’t appear to be black in the most superior parts due to these factors.  The first few times, the ILV is a bit hard, so ask for some assistance.  But keep in mind the ILV is a continuous space and this will help you determine the true borders. Also review the isolated ventricular picture presented in the first part of the guide to help you understand what the ILV should appear to be.

Finally, keep in mind that the tail of the caudate is something to attend to as you segment the ILV.  It is labeled above with an asterisk (*). All this is to say that the ILV is difficult to segment accurately with a threshold tool, and better to use the draw tool unthresholded.

In more anterior sections than the above, the ILV will form a crescent over the hippocampus that extends from the medial surface to the dorsal surface, and is bounded medially by the fornix (vide supra).  There is a membrane that extends from the fornix superiorly to wall off the lateral ventricle. When the fornix disappears as a coherent entity, great care must be taken to determine the medial border of the ILV.  In the image below, the ILV on the left hand side of the image (green dashed line) is relatively clear.  On the right side of the image, the ILV appears disconnected into a portion laterally to the hippocampus, and a portion immediately superior to the hippocampus.  The superior space will probably not extend to the portion immediately ventral to the optic tract, but here you need to go back and forth in the coronal series to convince yourself of this. This approach will also help you to determine whether the two spaces are actually connected and the linkage obscured by partial voluming.  It is extremely likely this is the case since the space is coherent; in this instance, the two ‘parts’ of the ILV are connected but that connection is not immediately seen.  Connect the two parts with a line a single voxel thick.  Review the ILV on the 3D and make sure there aren’t any holes in the contour.

<img src="https://lh3.googleusercontent.com/TlhfoRNp0qOvajpIWBGeXpIe_AbK-2op43sY5pfw3CnfArhwZ3QQLcVXKdVIl2H4pF2vm0zYvTBb" alt="" title="ILV ant">

A further consideration is that the hippocampus  tends to have visible holes in it (e.g., blood vessels) that may not explicitly communicate with the ventricle. Some of them do, some are blind, and some communicate with the subarachnoid space outside of the brain.  When you segment, make sure you follow any questionable spaces  forward or backward in the coronal sections to convince yourself it is ventricle.

A final point is that the subarachnoid space that surrounds the brain is not directly contiguous with the ILV, although in some brains, the spaces appear to be continuous. In these cases, remember to use the fornix as your guide and landmark.

Don’t forget to evaluate the ILV on the different views, and in the 3D.

## The amygdala

The amygdala is located anteriorly and superiorly to the hippocampus.  It is named for its almond shape, but that shape is difficult to appreciate.  The amydala has indisinct boundaries with several structures which makes segmenting it a challenge.

Start with a section where the amygdala has relatively clear borders, such as the image below.

<img src="https://lh3.googleusercontent.com/anyplA-ZsuSJbp_cKsv6vyyviTI063uxQf8N9Aok1-_HXJG80tUSYbM1ZB266eROn1e45YMEsELi" alt="" title="Amy Mid">

On the right side of the image, notice the bottom red arrow.  This is where the white matter of the temporal lobe takes a right-angle turn to a superior and medial orientation.  If we follow it to the medial brain surface (upper arrow), it will form a border for the amygdala, as done on the left hand side of the image.  The border then continues medially and superiorly under the optic tract, curves inferiorly and then follows the white matter until the origin.

If we move posteriorly, recall that the tip of the hippocampus appears along the inferior and medial border of the amygdala (white dashed lines).

<img src="https://lh3.googleusercontent.com/3-MsbjejzqtmVXCU-q7P5A8KG-YqKskgpw5ezHvDEzGrKKjmgc9LI-Yt-qIutQ_q901e8bmIWJqv" alt="" title="Post Amy">

Notice that the introduction of the amygdala displaces the inferior border, but the superior borders are fairly consistent with the description above (under the optic tract).  If you look carefully at the above image, you’ll note the tail of the putamen on the left side of the image is present and disconnected from the amygdala, whereas on the right, the putamen would end directly above the amygdala.

Posteriorly from this location, the amygdala will diminish in size and the hippocampus increases in size.  In this image below (seen previously in the hippocampal section), the amygala is shown on the right side above the hippocampus with clear medial, superior and lateral borders.  On the left side, the amygdala has almost disappeared, but there is still a bit left.  When segmenting, keep your eyes open for the structure at the tip of the arrow.  This is the tail of the caudate.  It is variable in its appearance (i.e., it is clear in some but not all brains) and it is close to the amygdala.

<img src="https://lh3.googleusercontent.com/nydG37wzIQkDipb81dy5_BA2u4Hi8bn7UIDaMnbATCiRVDzK_iQ_GZOwZ-lK9vR90kvm1eLpDdHq" alt="" title="post Amy">

Now that you have demarcated the amygdala posteriorly, turn to its anterior extent.  Start in the coronal section in which we began the amygdalar segmentation, and move ante, keeping the borders consistent from slice to slice.  This will work well, but at a certain point, things will change as the amygdala comes to an end. This is tricky and variable from section to section.

In the image below, the left side of the image displays the amygdala as outline previously, except for the fact that the gray matter laterally to the optic tract is not segmented.  Instead, the border follows the subarachnoid space on the medial aspect of the hemisphere laterally under the optic tract, then down to complete the border.

<img src="https://lh3.googleusercontent.com/CJrzIDdaalNpM-WY63CZUKM8_Gg4-a5383ahy7f_itxDyIWCwlPiCVJQsk-9n7vXZ0Py0llMDRoa" alt="" title="Ant Amy">

On the right side of the image, notice that the red dashed line has been displaced.  Recall that the right side of the image is a bit more anterior than the left side.  What is happening is that there is a cortex that is present, and the amygdala will come to be directly under that cortex. In some brains, changing the contrast reveals a circular structure at this level.  This circular structure shrinks in the next anterior section and disappears in two sections.  Segmentation of this anterior region of the amygdala benefits from noodling around with the brightness and contrast, and looking at the T2 image set.

## Final Quality Control

Now that you’ve completed segmenting the internal brain structures, it is time to review it.  You’ve just completed a lot of work, and errors are bound to creep in.  As you develop your skills, you’ll preempt these errors.  At this stage, it is nice to take a look at the segmentation in a systematic way to make sure everything is the way you’d like it / the way it should be.  Below is a list of things that are often overlooked that it is good to check on, according to structure.  You should have done an initial QC step after each segmentation to make sure the axial and sagittal borders are not subject to staircase errors.  In this part, you’ll review the entire segmentation.

It is important to be systematic about this, and go structure by structure.  Start with the lateral ventricles, and move down the list.  Resist seeing an error in a subsequent segmentation (“Oh man, let me just fix this small error in the amygdala”) because that leads to a downward spiral and then you wake up 30 minutes later.  Keep your focus on each segment.  As you do, keep in mind the following points.

***Lateral Ventricles***

- Is the lateral ventricle body connected with occipital horn?  Recall that you may need to infer a connection.
- Is the choroid plexus consistently and completely included in the ventricle
- Check to make sure the foramen of Monro extends to clasp the side of the third ventricle
- Turn opacity on all the way to see if there are any aberrant ventricle voxels below the fornix, in the transverse cerebral fissure, or any other interesting places.
- Make sure that that medial border of each (along the septum pellucidum) is consistent across sections.  While in some cases, the two pellucida may be fused and a common line is possible, in most cases, the medial border of each ventricle is separated by at least 1 voxel.
- Check to see on the 3D view whether there are holes or discontinuities.  Make sure the smoothing is set to ~0.3 so you can identify discrepancies (this setting is in segment editor on the down arrow next to the 3D button above the segment structure list.

***Third Ventricle***

- Check on the mid sagittal view to makes sure the third ventricle extends to the ‘W’ shape anteriorly and inferiorly, and above the pineal gland posteriorly and superiorly.

***Fourth Ventricle***
- Is the floor of the fourth ventricle smooth?  Does the 3D look like a fourth ventricle?
- Is the cerebral aqueduct / medial aperture present at the anterior end?  Make sure that there are at least 2 x 2 voxels
- Is the choroid plexus included in the ventricle at the inferior border?
- Check the axial view to make sure the lateral apertures are appropriate.

***Nucleus Accumbens***

- Make sure the line between the NAC and the ventral border of the anterior limb of the internal capsule is consistent.

***Caudate***
- Confirm that there are no ‘holes’ in the caudate and putamen (when viewed in 3D). It helps to set the opacity of the segments to 100%.
- Make sure the caudate doesn’t extend too dorsally along the course of its body, or wraps around the ventricle to appear above the ventricle.

***Putamen***
- Make sure the putamen extends posteriorly enough.
- Make sure the ventral border is consistent, and extends in ventral region only in its more posterior portion.

***Globus pallidus***
- Check on 3D to make sure it is a consistent shape.
- Double check the T2.
- Make sure to double check and confirm the posterior tail as well as the inferior border.

***Brainstem***
- Start on the midsagittal view to confirm the line between the posterior commissure and the prepontine fissure is straight
- Move to parasagittal sections to verify that the border between the brainstem and the fourth ventricle is consistent and correct

***Thalamus***
- Make sure the inferior border of the thalamus is the hypothalamic fissure (where it appears).
- Make sure that where the thalami come together, they meet along the midline, and that the line between L and R is consistent across sections. Use filled opacities to make sure there are no unfilled voxels.  It is useful to use sagittal sections for this…
- Check the posterior aspect of the thalamus to make sure it is included.
- Go through the sagittal sections to make sure voxels do not intrude into the fornix or the ventricles.  Confirm the anterior portion of the thalamus using parasagittal sections.
- Make sure you’re comfortable with the lateral borders.

***VDC***
- Make sure the upper border of the VDC is at the hypothalamic sulcus, and its lateral-inferior border is the optic tract/LGN.
- Make sure the VDC border doesn’t rise above the horizontal line that extends laterally from the sulcus.
- Make sure that when L and R VDC meet on the midline, they meet in the same plane and have no holes.  Make sure this plane is the same as the one that divides the left and right thalami.
- Confirm that the VDC includes the LGN.
- Make sure the VDC goes below the third ventricle and meets its partner.
- Make sure the VDC includes the habenulae and the posterior commissure.

***Inferior horn of the lateral ventricle***
- Make sure it is complete and connected (no holes).

***Hippocampus***
- Check medial border for consistency.
- Double check the hippocampus posterior to the thalamus.

***Amygdala***
- 3D viewing helps with the anterior amygdala.

## Final Comments
The first brain you do is really hard.  The second is
easier. Then the third and the fourth are hard.  Keep at it.  Things will get much easier as you go.

Oh, and if you see evidence of a structure that doesn’t look like you don’t think it should, please ask.  Some brains will have frank pathology and you shouldn’t segment if you see something that isn’t right.

When in doubt, ask for help.  Ask questions.  At the very least, you’ll get clarification.  At the most, your penetrating intellect will reveal a better way to segment.
