import logging
import os

import qt
import vtk

import slicer

from SegmentEditorEffects import *


class MoveSegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
    """This effect uses Watershed algorithm to partition the input volume"""

    SOURCE_SEGMENT_ID_PARAMETER = "SourceSegmentID"
    SOURCE_SEGMENTATION_REFERENCE = "MoveSegments.SourceSegmentation"

    def __init__(self, scriptedEffect):
        scriptedEffect.name = 'Move segments'
        scriptedEffect.perSegment = True
        scriptedEffect.requireSegments = True  # this effect requires segment(s) existing in the segmentation
        AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

    def clone(self):
        # It should not be necessary to modify this method
        import qSlicerSegmentationsEditorEffectsPythonQt as effects
        clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
        clonedEffect.setPythonSource(__file__.replace('\\', '/'))
        return clonedEffect

    def icon(self):
        # It should not be necessary to modify this method
        iconPath = os.path.join(os.path.dirname(__file__), 'MoveSegmentEditorEffect.png')
        if os.path.exists(iconPath):
            return qt.QIcon(iconPath)
        return qt.QIcon()

    def helpText(self):
        return """Move a segment from another segmentation into the selected segment."""

    def setupOptionsFrame(self):
        # Object scale slider
        self.segmentSelectorWidget = slicer.qMRMLSegmentSelectorWidget()
        self.segmentSelectorWidget.setToolTip('Choose the segment to copy the segment from.')
        self.segmentSelectorWidget.setMRMLScene(slicer.mrmlScene)
        self.scriptedEffect.addLabeledOptionsWidget("Source segment:", self.segmentSelectorWidget)
        self.segmentSelectorWidget.connect('currentNodeChanged(vtkMRMLNode*)', self.updateMRMLFromGUI)
        self.segmentSelectorWidget.connect('currentSegmentChanged(QString)', self.updateMRMLFromGUI)

        # Apply button
        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.objectName = self.__class__.__name__ + 'Apply'
        self.applyButton.setToolTip("Move segment from the source to the destination segment.")
        self.scriptedEffect.addOptionsWidget(self.applyButton)
        self.applyButton.connect('clicked()', self.onApply)

    def createCursor(self, widget):
        # Turn off effect-specific cursor for this effect
        return slicer.util.mainWindow().cursor

    def setMRMLDefaults(self):
        self.scriptedEffect.setParameterDefault(self.SOURCE_SEGMENT_ID_PARAMETER, "Test")

    def updateGUIFromMRML(self):
        wasBlocking = self.segmentSelectorWidget.blockSignals(True)
        self.segmentSelectorWidget.setCurrentNode(self.scriptedEffect.parameterSetNode().GetNodeReference(self.SOURCE_SEGMENTATION_REFERENCE))
        self.segmentSelectorWidget.setCurrentSegmentID(self.scriptedEffect.parameter(self.SOURCE_SEGMENT_ID_PARAMETER))
        self.segmentSelectorWidget.blockSignals(wasBlocking)

    def updateMRMLFromGUI(self):
        self.scriptedEffect.parameterSetNode().SetNodeReferenceID(self.SOURCE_SEGMENTATION_REFERENCE, self.segmentSelectorWidget.currentNodeID())
        self.scriptedEffect.setParameter(self.SOURCE_SEGMENT_ID_PARAMETER, self.segmentSelectorWidget.currentSegmentID())

    def onApply(self):
        # This can be a long operation - indicate it to the user
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

        # Allow users revert to this state by clicking Undo
        self.scriptedEffect.saveStateForUndo()

        modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()
        originalImageToWorldMatrix = vtk.vtkMatrix4x4()
        modifierLabelmap.GetImageToWorldMatrix(originalImageToWorldMatrix)

        sourceSegmentation = self.segmentSelectorWidget.currentNode()
        sourceSegmentID = self.segmentSelectorWidget.currentSegmentID()

        sourceLabelmap = slicer.vtkOrientedImageData()
        sourceSegmentation.GetBinaryLabelmapRepresentation(sourceSegmentID, sourceLabelmap)

        slicer.vtkOrientedImageDataResample.ResampleOrientedImageToReferenceOrientedImage(sourceLabelmap, modifierLabelmap, modifierLabelmap)

        # Apply changes
        self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeSet)

        qt.QApplication.restoreOverrideCursor()
