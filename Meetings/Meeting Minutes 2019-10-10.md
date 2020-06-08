# Meeting 2019-10-10

Minutes from meeting PNL/Queens Collaboration Skype Call – 10:30am
* PNL: Sylvain Bouix (SB), Jarrett Rushmore (JR)
* Queens: Kyle Sunderland (KS, Andras Lasso (AL)


## 1.	 Multiregion segmentation (KS)
* a.	Performed by merging binary labelmap segmentations
* b.	Reduces processing and saving times considerably
* c.	Effective as long as segments don’t overlap
* d.	Will be up by 11/11/19

## 2.	Cropping Question (SB)
* a.	Difference in labelmap and grayscale images; seems to autocrop
* b.	AL: agree improvement would be nice; for now, export with Reference Volume selected in Segmentations module

## 3.	Surface Drawing (AL)
* a.	Some prototyping done
* b.	Question: How are points defined, and how are they drawn (surface, vertices?)
* c.	1990’s C code is likely an answer; sense from SB is that line runs through vertices
* d.	Line is not a straight line – probably need to constrain to surface points (not vertices?)
* e.	TO DO: ask George P for surface files
* f.	AL - Use lines to cut through surface?
* g.	SB – should be a 1:1 mapping from outer to inner surface (pial to WM), lines may not be orthogonal; may depend on 3D shape of sulcus; use mapping to cut voxels; may be weighted based on curvature rather than pure shortest distance
* h.	TO DO: try to dig up 1990s C-code, 

## 4.	Question about Markdown language 
* a.	Use github, external MD editor (e.g., StackEdit)

## 5.	Histogram
* a.	Initial screen sharing showed considerable promise
* b.	Would help to have a graph (like CardViews) pop up during histogram process

## 6.	Next meeting : 11/7/19: 10:30am
