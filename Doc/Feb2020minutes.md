# Meeting 2020-02-19

Minutes from meeting PNL/Queens Collaboration Skype Call – 2:00pm
* PNL:  Jarrett Rushmore (JR), Sylvian Bouix (SB)
* Queens: Kyle Sunderland (KS), Andras Lasso (AL)


## 1.	 Surface Creation

* KS showed implementation of Dijkstra algorithm on freesurfer WM surface
  Includes ability to incoporate scalar values, on-line modification,  UI-based control point modifiction of surfaces
  Incorporates ability to use differet scalar features, or combinations thereof (e.g., sulcal eight, curve, etc) to weight line
  
  *KS will experiment a bit on weighting the lines with a combination of features based on previous approaches
  
## 2.  Cutting it up

* The cortex will be divided up into segments based on:
  - Curves defined by the above lines
  - Coronal or oblique planes defined by the user (i.e., established definitions)
    -planes will be established by three points
  - Curves and planes will form the borders of each segmentation, and the distance between the WM surface and the Pial surface at those points will define the cortical ribbon
  
  * Need to establish that WM vertices correspond in a 1:1 fashion to specific pial vertices.
  
## 3.  Query Language and grammar
 * It would be useful to have a grammar similar to the WMQL (see email from SB 2/19/20) to implement cutting/parcellation rules
  -this would allow people like JR to be able to modify definitions as they evolve
  
  * SB may reach out to David Kennedy to inquire more about the Cardview file format
  * AL suggests the .json or .csv are most tractable, and it would not be worth while to develop a dedicated parser.
  * concensus appears to be that the WMQL language would be most versitile
 

## 2.	Action Items
  1. Create modules that takes curves and points with text field specifying rules.
  2. Cut and extract segments based on rules
  2. Use WMQL lexicon to write rules 
  3. Verify WM and Pial Vertex correspondance
  
## 3.	Next meeting : 03/18/2020: 2:00pm
