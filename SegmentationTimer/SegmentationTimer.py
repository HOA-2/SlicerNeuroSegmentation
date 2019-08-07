import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from datetime import datetime

#
# SegmentationTimer
#

class SegmentationTimer(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Segmentation Timer"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = ["Segmentations"]
    self.parent.contributors = ["Kyle Sunderland (Perk Lab, Queen's University)"]
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

    if not slicer.app.commandOptions().noMainWindow :
      slicer.app.connect("startupCompleted()", self.initializeModule)

  def initializeModule(self):
    slicer.modules.segmentationtimer.widgetRepresentation()
    userInfo = slicer.app.applicationLogic().GetUserInformation()
    name = userInfo.GetName()

    message = "User name is not set.\n"
    if name != "":
      message = "The current user name is: " + name + ".\n"
    message += "\nIf you would to change the user name, it can be changed in the application menu under:\n"\
               "Edit -> Application Settings -> User -> Name\n"

    slicer.util.infoDisplay(message, dontShowAgainSettingsKey = "SegmentationTimer/DontShowSomeMessage")

#
# SegmentationTimerWidget
#

class SegmentationTimerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self._parameterNode = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = SegmentationTimerLogic()
    # This will use createParameterNode with the provided default options
    self.setParameterNode(self.logic.getParameterNode())

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/SegmentationTimer.ui'))
    self.layout.addWidget(uiWidget)

    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.tableNodeSelector.addAttribute("vtkMRMLTableNode", "SegmentationTimer.TableNode", "")
    self.ui.segmentationTimer.setMRMLScene(slicer.mrmlScene)
    # Connections
    self.ui.tableNodeSelector.nodeAdded.connect(self.onNodeAdded)
    self.ui.tableNodeSelector.currentNodeChanged.connect(self.onCurrentNodeChanged)


  def cleanup(self):
    pass

  def onNodeAdded(self, node):
    self.logic.setupTimerTableNode(node)

  def onCurrentNodeChanged(self, node):
    currentNode = self.ui.tableNodeSelector.currentNode()
    self.logic.setSegmentationTimerTableNode(currentNode)

  def parameterNode(self):
    return self._parameterNode

  def setParameterNode(self, inputParameterNode):
    if inputParameterNode == self._parameterNode:
      return
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGuiFromMRML)
    if inputParameterNode is not None:
      self.addObserver(inputParameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGuiFromMRML)
    self._parameterNode = inputParameterNode

  def updateGuiFromMRML(self, caller=None, event=None, callData=None):
    currentNode = self._parameterNode.GetNodeReference(self.logic.SEGMENTATIONTIMER_TABLE_REFERENCE_ROLE)
    self.ui.tableNodeSelector.setCurrentNode(currentNode)

class SegmentationTimerLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):

  SEGMENTATIONTIMER_TABLE_REFERENCE_ROLE = "segmentationTimerTableRef"

  DATE_FORMAT = "%m/%d/%Y, %H:%M:%S"

  COMPUTER_COLUMN_NAME = 'computer'
  USER_COLUMN_NAME = 'user'
  MASTER_VOLUME_COLUMN_NAME = 'mastervolume'
  STARTTIME_COLUMN_NAME = 'starttime'
  SCENE_COLUMN_NAME = 'scene'
  SEGMENTATION_COLUMN_NAME = 'segmentation'
  SEGMENT_COLUMN_NAME = 'segment'
  TERMINOLOGY_COLUMN_NAME = 'terminology'
  OPERATION_COLUMN_NAME = 'operation'
  DURATION_COLUMN_NAME = 'duration'
  timerTableColumnNames = [
    COMPUTER_COLUMN_NAME,
    USER_COLUMN_NAME,
    MASTER_VOLUME_COLUMN_NAME,
    STARTTIME_COLUMN_NAME,
    SCENE_COLUMN_NAME,
    SEGMENTATION_COLUMN_NAME,
    SEGMENT_COLUMN_NAME,
    TERMINOLOGY_COLUMN_NAME,
    OPERATION_COLUMN_NAME,
    DURATION_COLUMN_NAME
  ]

  timerTableColumnTypes = {
    COMPUTER_COLUMN_NAME: 'string',
    USER_COLUMN_NAME: 'string',
    MASTER_VOLUME_COLUMN_NAME : 'string',
    STARTTIME_COLUMN_NAME: 'string',
    SCENE_COLUMN_NAME: 'string',
    SEGMENTATION_COLUMN_NAME: 'string',
    SEGMENT_COLUMN_NAME: 'string',
    TERMINOLOGY_COLUMN_NAME: 'string',
    OPERATION_COLUMN_NAME: 'string',
    DURATION_COLUMN_NAME: 'double'
  }
  activeRows = {}

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    VTKObservationMixin.__init__(self)

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

    self.selectSegmentationTimerTableNode()
    self.addSegmentEditorObservers()

    self.sceneClosedTimer = qt.QTimer()
    self.sceneClosedTimer.setInterval(100)
    self.sceneClosedTimer.setSingleShot(True)
    self.sceneClosedTimer.timeout.connect(self.selectSegmentationTimerTableNode)

  def onSceneEndClose(self, caller, event):
    self.sceneClosedTimer.start()

  def onSceneEndImport(self, caller, event):
    self.sceneClosedTimer.start()

  def selectSegmentationTimerTableNode(self):
    tableNode = self.getTimerTableNode()
    if not tableNode is None:
      return

    tableNode = slicer.vtkMRMLTableNode()
    tableNode.SetName("SegmentationTimerNode")
    tableNode.SetAttribute("SegmentationTimer.TableNode", "")
    slicer.mrmlScene.AddNode(tableNode)
    self.setupTimerTableNode(tableNode)
    self.setSegmentationTimerTableNode(tableNode)

  def getTimerTableNode(self):
    parameterNode = self.getParameterNode()
    if parameterNode is None:
      return
    return parameterNode.GetNodeReference(self.SEGMENTATIONTIMER_TABLE_REFERENCE_ROLE)

  def setupTimerTableNode(self, tableNode):
    if tableNode is None:
      return
    tableNode.RemoveAllColumns()
    for name in self.timerTableColumnNames:
      type = self.timerTableColumnTypes[name]
      column = tableNode.AddColumn()
      column.SetName(name)
      column.SetName(name)
      tableNode.SetColumnProperty(name, "type", type)
    tableNode.SetUseFirstColumnAsRowHeader(False)
    tableNode.SetUseColumnNameAsColumnHeader(True)

  def addSegmentEditorObservers(self):
    editorNodes = slicer.util.getNodesByClass("vtkMRMLSegmentEditorNode")
    for editorNode in editorNodes:
      self.observeSegmentEditorNode(editorNode)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, callData):
    if isinstance(callData, slicer.vtkMRMLSegmentEditorNode):
      self.observeSegmentEditorNode(callData)

  def observeSegmentEditorNode(self, editorNode):
    self.addObserver(editorNode, vtk.vtkCommand.ModifiedEvent, self.onEditorNodeModified)
    self.onEditorNodeModified(editorNode)

  def onEditorNodeModified(self, editorNode, event=None, callData=None):
    tableNode = self.getTimerTableNode()
    if editorNode is None or tableNode is None:
      return
    if not editorNode in self.activeRows:
      self.setActiveRow(editorNode, -1)

    serializedActiveRow = self.serializeActiveRow(editorNode)
    serializedEditorNode = self.serializeEditorNode(editorNode)
    if self.activeRows[editorNode] == -1 or serializedActiveRow != serializedEditorNode:
      row = tableNode.AddEmptyRow()
      self.setActiveRow(editorNode, row)

  def serializeEditorNode(self, editorNode):
    if editorNode is None:
      return ""

    activeState = SegmentEditorState()
    selectedSegmentID = ""
    if editorNode.GetSelectedSegmentID():
      selectedSegmentID = editorNode.GetSelectedSegmentID()
    segmentationNode = editorNode.GetSegmentationNode()
    if segmentationNode is not None:
      activeState.segmentationNodeName = segmentationNode.GetName()
      segmentation = segmentationNode.GetSegmentation()
      segment = segmentation.GetSegment(selectedSegmentID)
      if segment is not None:
        tag = vtk.mutable("")
        segment.GetTag(segment.GetTerminologyEntryTagName(), tag)
        activeState.terminology = tag.get()
        activeState.segmentName = segment.GetName()
    activeState.activeEffect = editorNode.GetActiveEffectName()
    return activeState.serialize()

  def serializeActiveRow(self, editorNode):
    if editorNode is None:
      return ""

    activeState = SegmentEditorState()
    activeState.segmentName = self.getActiveSegmentName(editorNode)
    activeState.segmentationNodeName = self.getActiveSegmentationNodeName(editorNode)
    activeState.activeEffect = self.getActiveEditorEffect(editorNode)
    activeState.terminology = self.getActiveTerminology(editorNode)
    return activeState.serialize()

  def updateAllActiveRows(self, caller=None, event=None, callData=None):
    for editorNode in self.activeRows.keys():
      self.updateActiveRow(editorNode)

  def updateActiveRow(self, editorNode, columns=[]):
    if not editorNode in self.activeRows:
      return
    activeRow = self.activeRows[editorNode]
    if activeRow == -1:
      return

    tableNode = self.getTimerTableNode()
    if tableNode is None:
      return

    for column in range(tableNode.GetNumberOfColumns()):
      name = tableNode.GetColumnName(column)
      if columns != [] and not name in columns:
        continue

      value = ""

      if name == self.COMPUTER_COLUMN_NAME:
        hostInfo = qt.QHostInfo()
        value = hostInfo.localHostName()

      elif name == self.USER_COLUMN_NAME:
        userInfo = slicer.app.applicationLogic().GetUserInformation()
        value = userInfo.GetName()

      elif name == self.MASTER_VOLUME_COLUMN_NAME:
        masterVolume = editorNode.GetMasterVolumeNode()
        if masterVolume:
          value = masterVolume.GetName()

      elif name == self.STARTTIME_COLUMN_NAME:
        if tableNode.GetCellText(activeRow, column) == "":
          value = datetime.now().strftime(self.DATE_FORMAT)

      elif name == self.SCENE_COLUMN_NAME:
        pass

      elif name == self.SEGMENTATION_COLUMN_NAME:
        segmentationNode = editorNode.GetSegmentationNode()
        if segmentationNode is not None:
          value = segmentationNode.GetName()

      elif name == self.SEGMENT_COLUMN_NAME:
        if segmentationNode is not None:
          segmentation = segmentationNode.GetSegmentation()
          if editorNode.GetSelectedSegmentID():
            segment = segmentation.GetSegment(editorNode.GetSelectedSegmentID())
            if segment:
              value = segment.GetName()

      elif name == self.TERMINOLOGY_COLUMN_NAME:
        if segmentationNode is not None:
          segmentation = segmentationNode.GetSegmentation()
          if editorNode.GetSelectedSegmentID():
            segment = segmentation.GetSegment(editorNode.GetSelectedSegmentID())
            if segment is not None:
              tag = vtk.mutable("")
              segment.GetTag(segment.GetTerminologyEntryTagName(), tag)
              value = tag.get()

      elif name == self.OPERATION_COLUMN_NAME:
        value = editorNode.GetActiveEffectName()

      elif name == self.DURATION_COLUMN_NAME:
        value = str((datetime.now() - self.getActiveStartTime(editorNode)).total_seconds())

      else:
        continue
      tableNode.SetCellText(activeRow, column, value)

  def setActiveRow(self, editorNode, row):
    if editorNode in self.activeRows:
      if self.activeRows[editorNode] == row:
        return
    self.updateActiveRow(editorNode, [self.DURATION_COLUMN_NAME])
    self.activeRows[editorNode] = row
    self.updateActiveRow(editorNode)

  def getActiveStartTime(self, editorNode):
    tableNode = self.getTimerTableNode()
    if tableNode is None or editorNode is None:
      return datetime.now()
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return datetime.now()
    startText = tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(self.STARTTIME_COLUMN_NAME))
    if startText == "":
      return datetime.now()
    return datetime.strptime(startText, self.DATE_FORMAT)

  def getActiveEditorEffect(self, editorNode):
    tableNode = self.getTimerTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(self.OPERATION_COLUMN_NAME))

  def getActiveSegmentationNodeName(self, editorNode):
    tableNode = self.getTimerTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(self.SEGMENTATION_COLUMN_NAME))

  def getActiveSegmentName(self, editorNode):
    tableNode = self.getTimerTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(self.SEGMENT_COLUMN_NAME))

  def getActiveTerminology(self, editorNode):
    tableNode = self.getTimerTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(self.TERMINOLOGY_COLUMN_NAME))

  def setSegmentationTimerTableNode(self, node):
    parameterNode = self.getParameterNode()
    if parameterNode is None:
      return
    if node is self.getTimerTableNode():
      return
    for editorNode in self.activeRows.keys():
      self.setActiveRow(editorNode, -1)
    nodeID = ""
    if node:
      nodeID = node.GetID()
    parameterNode.SetNodeReferenceID(self.SEGMENTATIONTIMER_TABLE_REFERENCE_ROLE, nodeID)

class SegmentEditorState():
  segmentationNodeName = ""
  segmentName = ""
  activeEffect = ""
  terminology = ""

  def serialize(self):
    if self.segmentationNodeName == None:
      self.segmentationNodeName = ""
    if self.segmentName == None:
      self.segmentName = ""
    if self.activeEffect == None:
      self.activeEffect = ""
    if self.terminology == None:
      self.terminology = ""

    output = ""
    output += self.segmentationNodeName + ","
    output += self.segmentName + ","
    output += self.activeEffect + ","
    output += self.terminology + ","
    return output

class SegmentationTimerTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SegmentationTimer1()

  def test_SegmentationTimer1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    self.delayDisplay('Test passed!')
