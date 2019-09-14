Meeting 2019-09-12
==================

Minutes from meeting: PNL/Queens Collaboration Skype Call – 11:00am 
- PNL: Sylvain Bouix (SB), Jarrett Rushmore (JR)
- Queens: Kyle (kyle.sunderland (KS)) and Andras Lasso (AL) 

Agenda for collaboration (long-term)
------------------------------------

- Neurosegmentation Module 
- Tablet – needs to upgrade build 
- Histogram 
- Surface Draw 
- Cortical Parcellation 

Topic 1: Surface drawing is the next project
--------------------------------------------

- Specify weights via euclidian minimization between nodes (start here), perhaps with control points  
- Similar to what Nikos Makris and Rudolf Pinard worked together to do around a decade ago (probably in C) 
- Shortest path algorithm is already in in surface VTK 
- AL: what happens after lines are drawn? 
- Use lines to cut up surface, needs careful design  
- Probably provide query using txt file containing rules for landmarks/boundaries/rules; algorithm uses text file input to chop up cortex 
- Shouldn’t be hard coded, since rules will change 
- TO DO: Provide example text file  (from WMQL) for AL/KS (https://github.com/PerkLab/BwhNeuroImagingCollab/issues/16)

TOPIC #2: Interoperability between FreeSurfer and Slicer
--------------------------------------------------------

- Free view export is not perfect, there are some transforms. 
- TO DO: Send examples to Queens (https://github.com/PerkLab/BwhNeuroImagingCollab/issues/17)
- AL: Slicer has importers, may have to update 

TOPIC #3: Multiple Segments
---------------------------

Working on improving performance with multiple (I.e., 100s) segments 

TOPIC #4: Formats
-----------------

- Segmentation output will ultimately be a bunch of lines, segments, etc 
- what is the underlying segment file? 
- AL: Could store some as arbitrary metadata (e.g., 4D .nrrd) 
- Could store points and lines in a volume file as custom metadata 
- If there is a specific format we need, could do that 
- Would be nice to be able to ‘Save’ within a scene as well as to Export (e.g., to a FreeSurfer specific file) 
 
**Next Skype meeting October 10th, 10:30** 
