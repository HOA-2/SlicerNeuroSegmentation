import logging
import os

import vtk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin


#
# MarkupsSnap
#

class MarkupsSnap(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Markups Snap"
        self.parent.categories = ["HOA 2", "Neuro Segmentation and Parcellation", "Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Kyle Sunderland (Perk Lab, Queen's University)"]
        self.parent.helpText = """
This module snaps a markup point to the closest point on another markup node.
"""
        self.parent.acknowledgementText = """
This file was originally developed by Kyle Sunderland (Perk Lab, Queen's University), and was partially funded by Brigham and Women's Hospital through NIH grant R01MH112748
"""

#
# MarkupsSnapWidget
#

class MarkupsSnapWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/MarkupsSnap.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)
        self.ui.parameterNodeSelector.addAttribute("vtkMRMLScriptedModuleNode", "ModuleName", self.moduleName)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = MarkupsSnapLogic()
        self.logic.setMRMLScene(slicer.mrmlScene)

        # Connections
        self.ui.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setParameterNode)
        self.ui.parameterNodeSelector.connect('nodeAdded(vtkMRMLNode*)', self.onParameterNodeAdded)
        self.ui.parameterNodeSelector.connect('nodeAdded(vtkMRMLNode*)', self.updateParameterNodeFromGUI)
        self.ui.anchorPointSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateParameterNodeFromGUI)
        self.ui.snapDistanceSlider.connect('valueChanged(double)', self.updateParameterNodeFromGUI)
        self.ui.activeButton.connect('clicked(bool)', self.updateParameterNodeFromGUI)

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()
        self.logic.removeObservers()

    def enter(self):
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    def onSceneStartClose(self, caller, event):
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onParameterNodeAdded(self, parameterNode):
      """
      Called if a node is added from the combobox.
      Sets the default node parameters.
      """
      self.logic.setDefaultParameters(parameterNode)

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if inputParameterNode:
            self.logic.setDefaultParameters(inputParameterNode)

        # Unobserve previously selected parameter node and add an observer to the newly selected.
        # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
        # those are reflected immediately in the GUI.
        if self._parameterNode is not None and self.hasObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode):
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        # Initial GUI update
        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        self._updatingGUIFromParameterNode = True

        # Update node selectors and sliders
        wasBlocking = self.ui.parameterNodeSelector.blockSignals(True)
        self.ui.parameterNodeSelector.setCurrentNode(self._parameterNode)
        self.ui.parameterNodeSelector.blockSignals(wasBlocking)

        wasBlocking = self.ui.anchorPointSelector.blockSignals(True)
        self.ui.anchorPointSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.ANCHOR_POINT_REFERENCE))
        self.ui.anchorPointSelector.blockSignals(wasBlocking)

        wasBlocking = self.ui.snapDistanceSlider.blockSignals(True)
        self.ui.snapDistanceSlider.value = self.logic.getDoubleParameter(self._parameterNode, self.logic.SNAP_DISTANCE_PARAMETER, default=0.0)
        self.ui.snapDistanceSlider.blockSignals(wasBlocking)

        wasBlocking = self.ui.snapAllCheckBox.blockSignals(True)
        self.ui.snapAllCheckBox.checked = self.logic.getSnapAll(self._parameterNode)
        self.ui.snapAllCheckBox.blockSignals(wasBlocking)
        self.ui.snapAllCheckBox.visible = False
        self.ui.snapAllLabel.visible = False

        wasBlocking = self.ui.activeButton.blockSignals(True)
        self.ui.activeButton.checked = self.logic.getBooleanParameter(self._parameterNode, self.logic.ACTIVE_PARAMETER, default=False)
        self.ui.activeButton.blockSignals(wasBlocking)

        wasBlocking = self.ui.outputMarkupsSelector.blockSignals(True)
        numberOfOutputReferences = self._parameterNode.GetNumberOfNodeReferences(self.logic.SNAP_NODE_REFERENCE)
        selectedNodes = []
        for i in range(numberOfOutputReferences):
            selectedNode = self._parameterNode.GetNthNodeReference(self.logic.SNAP_NODE_REFERENCE, i)
            selectedNodes.append(selectedNode)
        for i in range(self.ui.outputMarkupsSelector.nodeCount()):
            node = self.ui.outputMarkupsSelector.nodeFromIndex(i)
            if node in selectedNodes:
                self.ui.outputMarkupsSelector.check(node)
            else:
                self.ui.outputMarkupsSelector.uncheck(node)
        self.ui.outputMarkupsSelector.blockSignals(wasBlocking)
        self.ui.outputMarkupsSelector.visible = False
        self.ui.outputLabel.visible = False

        # All the GUI updates are done
        self._updatingGUIFromParameterNode = False

    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """
        This method is called when the user makes any change in the GUI.
        The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        with slicer.util.NodeModify(self._parameterNode):
          self._parameterNode.SetNodeReferenceID(self.logic.ANCHOR_POINT_REFERENCE, self.ui.anchorPointSelector.currentNodeID)
          self._parameterNode.SetParameter(self.logic.SNAP_DISTANCE_PARAMETER, str(self.ui.snapDistanceSlider.value))
          self._parameterNode.SetParameter(self.logic.ACTIVE_PARAMETER, str(self.ui.activeButton.checked))
          self._parameterNode.SetParameter(self.logic.SNAP_ALL_PARAMETER, str(self.ui.snapAllCheckBox.checked))

#
# MarkupsSnapLogic
#

class MarkupsSnapLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    ANCHOR_POINT_REFERENCE = "AnchorPointReference"
    SNAP_NODE_REFERENCE = "SnapNodeReference"
    SNAP_DISTANCE_PARAMETER = "SnapDistance"
    SNAP_ALL_PARAMETER = "SnapAll"
    ACTIVE_PARAMETER = "Active"

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
        VTKObservationMixin.__init__(self)
        self.isSingletonParameterNode = False
        self.mrmlScene = None

    def setMRMLScene(self, scene):
        """
        Called when the scene is initialized.
        """
        self.mrmlScene = scene
        self.removeObservers(self.onNodeAdded)
        self.addObserver(scene, slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)
        self.updateParameterNodeObservers()

    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        if parameterNode is None:
            return

        with slicer.util.NodeModify(parameterNode):
            if not parameterNode.GetParameter(self.SNAP_DISTANCE_PARAMETER):
                parameterNode.SetParameter(self.SNAP_DISTANCE_PARAMETER, "10.0")
            if not parameterNode.GetParameter(self.SNAP_ALL_PARAMETER):
                parameterNode.SetParameter(self.SNAP_ALL_PARAMETER, str(True))
            parameterNode.SetModuleName(self.moduleName)

    @vtk.calldata_type(vtk.VTK_OBJECT)
    def onNodeAdded(self, caller=None, event=None, callData=None):
        """
        Called when a new node is added to the scene.
        """
        self.updateParameterNodeObservers()

    def updateParameterNodeObservers(self):
        self.removeObservers(self.parameterNodeModified)
        self.removeObservers(self.markupsNodeModified)
        if self.mrmlScene is None:
            return

        # Add observer to all parameter nodes in the scene for the module
        scriptedNodes = self.mrmlScene.GetNodesByClass("vtkMRMLScriptedModuleNode")
        for i in range(scriptedNodes.GetNumberOfItems()):
            node = scriptedNodes.GetItemAsObject(i)
            if node.GetModuleName() == self.moduleName:
                self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.parameterNodeModified)

        markupsNodes = self.mrmlScene.GetNodesByClass("vtkMRMLMarkupsNode")
        for i in range(markupsNodes.GetNumberOfItems()):
            node = markupsNodes.GetItemAsObject(i)
            self.addObserver(node, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.markupsNodeModified)

    def getSnapAll(self, parameterNode):
        return self.getBooleanParameter(parameterNode, self.SNAP_ALL_PARAMETER, default=False)

    def getActive(self, parameterNode):
        return self.getBooleanParameter(parameterNode, self.ACTIVE_PARAMETER, default=False)

    def getBooleanParameter(self, parameterNode, parameterName, default=False):
        if parameterNode is None:
            return False
        return parameterNode.GetParameter(parameterName) == str(True)

    def getSnapDistance(self, parameterNode):
        return self.getDoubleParameter(parameterNode, self.SNAP_DISTANCE_PARAMETER, default=0.0)

    def getDoubleParameter(self, parameterNode, parameterName, default=0.0):
        if parameterNode is None:
            return default
        parameterString = parameterNode.GetParameter(parameterName)
        if parameterString is None or parameterString == "":
            return default
        return float(parameterString)

    def parameterNodeModified(self, parameterNode, event=None, callData=None):
        if parameterNode is None:
            return
        pass

    @vtk.calldata_type(vtk.VTK_INT)
    def markupsNodeModified(self, markupsNode, event=None, modifiedIndex=-1):
        if modifiedIndex is None or modifiedIndex < 0:
            return
        
        # TODO: In the future we will be able to specify which markups nodes will be snapped.
        # For now, we will snap all markups nodes.

        with slicer.util.NodeModify(markupsNode):
          modifiedPoint = [0,0,0]
          markupsNode.GetNthControlPointPosition(modifiedIndex, modifiedPoint)

          scriptedNodes = self.mrmlScene.GetNodesByClass("vtkMRMLScriptedModuleNode")
          for i in range(scriptedNodes.GetNumberOfItems()):
              parameterNode = scriptedNodes.GetItemAsObject(i)
              if parameterNode.GetModuleName() != self.moduleName:
                  continue
              if not self.getActive(parameterNode):
                  continue

              snapAll = self.getSnapAll(parameterNode)
              if snapAll is None:
                  continue

              numberOfAnchorNodes = parameterNode.GetNumberOfNodeReferences(self.ANCHOR_POINT_REFERENCE)
              if numberOfAnchorNodes == 0:
                  continue

              snapDistance = self.getSnapDistance(parameterNode)
              snapDistance2 = snapDistance*snapDistance
              for anchorNodeIndex in range(numberOfAnchorNodes):
                  anchorNode = parameterNode.GetNthNodeReference(self.ANCHOR_POINT_REFERENCE, anchorNodeIndex)
                  if anchorNode is None or markupsNode == anchorNode:
                      continue

                  anchorPosition = [0,0,0]
                  for anchorPointIndex in range(anchorNode.GetNumberOfControlPoints()):
                      anchorNode.GetNthControlPointPosition(anchorPointIndex, anchorPosition)
                      distance2BetweenPoints = vtk.vtkMath.Distance2BetweenPoints(modifiedPoint, anchorPosition)
                      if distance2BetweenPoints < snapDistance2:
                          positionStatus = markupsNode.GetNthControlPointPositionStatus(modifiedIndex)
                          markupsNode.SetNthControlPointPosition(modifiedIndex, anchorPosition[0], anchorPosition[1], anchorPosition[2], positionStatus)
                          break

#
# MarkupsSnapTest
#
class MarkupsSnapTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
