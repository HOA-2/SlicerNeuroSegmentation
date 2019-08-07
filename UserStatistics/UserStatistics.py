import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from datetime import datetime

#
# UserStatistics
#

class UserStatistics(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "User Statistics"
    self.parent.categories = ["Utilities"]
    self.parent.dependencies = ["Segmentations", "SegmentEditor"]
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
    slicer.modules.userstatistics.widgetRepresentation()
    userInfo = slicer.app.applicationLogic().GetUserInformation()
    name = userInfo.GetName()

    message = "User name is not set.\n"
    if name != "":
      message = "The current user name is: " + name + ".\n"
    message += "\nIf you would to change the user name, it can be changed in the application menu under:\n"\
               "Edit -> Application Settings -> User -> Name\n"

    #slicer.util.infoDisplay(message, dontShowAgainSettingsKey = "UserStatistics/DontShowSomeMessage")

#
# UserStatisticsWidget
#

class UserStatisticsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self._parameterNode = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = UserStatisticsLogic()
    # This will use createParameterNode with the provided default options
    self.setParameterNode(self.logic.getParameterNode())

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/UserStatistics.ui'))
    self.layout.addWidget(uiWidget)

    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.tableNodeSelector.addAttribute("vtkMRMLTableNode", "UserStatistics.TableNode", "")
    self.ui.userStatistics.setMRMLScene(slicer.mrmlScene)

    # Connections
    self.ui.tableNodeSelector.nodeAddedByUser.connect(self.onNodeAddedByUser)
    self.ui.tableNodeSelector.currentNodeChanged.connect(self.onCurrentNodeChanged)
    self.ui.mergeTablesButton.clicked.connect(self.onMergeStatisticTablesClicked)


  def cleanup(self):
    pass

  def onNodeAddedByUser(self, node):
    self.logic.setupTimerTableNode(node)

  def onCurrentNodeChanged(self, node):
    currentNode = self.ui.tableNodeSelector.currentNode()
    self.logic.setUserStatisticsTableNode(currentNode)

  def onMergeStatisticTablesClicked(self):
    checkedNodes = self.ui.mergeTablesNodeSelector.checkedNodes()
    self.logic.mergeStatisticsTableNodes(checkedNodes)

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
    currentNode = self._parameterNode.GetNodeReference(self.logic.USER_STATISTICS_TABLE_REFERENCE_ROLE)
    self.ui.tableNodeSelector.setCurrentNode(currentNode)

class UserStatisticsLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):

  USER_STATISTICS_TABLE_REFERENCE_ROLE = "userStatisticsTableRef"

  DATE_FORMAT = "%Y%m%d-%H%M%S"

  COMPUTER_COLUMN_NAME = 'computer'
  USER_COLUMN_NAME = 'userName'
  MASTER_VOLUME_COLUMN_NAME = 'masterVolumeName'
  STARTTIME_COLUMN_NAME = 'startTime'
  SCENE_COLUMN_NAME = 'scene'
  SEGMENTATION_COLUMN_NAME = 'segmentationName'
  SEGMENT_COLUMN_NAME = 'segmentName'
  TERMINOLOGY_COLUMN_NAME = 'segmentTerminology'
  MODULENAME_COLUMN_NAME = 'moduleName'
  OPERATION_COLUMN_NAME = 'operation'
  USERACTIVITY_COLUMN_NAMEs = 'userActivity'
  DURATION_COLUMN_NAME = 'durationSec'
  timerTableColumnNames = [
    STARTTIME_COLUMN_NAME,
    OPERATION_COLUMN_NAME,
    DURATION_COLUMN_NAME,
    SEGMENT_COLUMN_NAME,
    MASTER_VOLUME_COLUMN_NAME,
    SEGMENTATION_COLUMN_NAME,
    TERMINOLOGY_COLUMN_NAME,
    MODULENAME_COLUMN_NAME,
    COMPUTER_COLUMN_NAME,
    USER_COLUMN_NAME,
    SCENE_COLUMN_NAME,
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
    DURATION_COLUMN_NAME: 'double',
    MODULENAME_COLUMN_NAME: 'string',
  }
  activeRows = {}

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    VTKObservationMixin.__init__(self)

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

    self.selectUserStatisticsTableNode()
    self.addSegmentEditorObservers()

    self.sceneClosedTimer = qt.QTimer()
    self.sceneClosedTimer.setInterval(100)
    self.sceneClosedTimer.setSingleShot(True)
    self.sceneClosedTimer.timeout.connect(self.selectUserStatisticsTableNode)

    #slicer.util.moduleSelector().selectModule('ModelMaker')
    slicer.util.moduleSelector().moduleSelected.connect(self.updateAllActiveRows)

  def onSceneEndClose(self, caller, event):
    self.sceneClosedTimer.start()

  def onSceneEndImport(self, caller, event):
    self.sceneClosedTimer.start()

  def mergeStatisticsTableNodes(self, tableNodes):
    if len(tableNodes) < 2:
      return
    original = tableNodes[0]
    for tableNode in tableNodes:
      if tableNode is not original:
        slicer.mrmlScene.RemoveNode(tableNode)

  def selectUserStatisticsTableNode(self):
    tableNode = self.getTimerTableNode()
    if not tableNode is None:
      return

    tableNode = slicer.vtkMRMLTableNode()
    tableNode.SetName("UserStatisticsTableNode")
    tableNode.SetAttribute("UserStatistics.TableNode", "")
    slicer.mrmlScene.AddNode(tableNode)
    self.setupTimerTableNode(tableNode)
    self.setUserStatisticsTableNode(tableNode)

  def getTimerTableNode(self):
    parameterNode = self.getParameterNode()
    if parameterNode is None:
      return
    return parameterNode.GetNodeReference(self.USER_STATISTICS_TABLE_REFERENCE_ROLE)

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
    if tableNode is None:
      return
    if not editorNode in self.activeRows:
      self.setActiveRow(editorNode, -1)

    serializedScene = self.serializeFromScene(editorNode)
    serializedTable = self.serializeFromTable(editorNode)
    if self.activeRows[editorNode] == -1 or serializedScene != serializedTable:
      row = tableNode.AddEmptyRow()
      self.setActiveRow(editorNode, row)

  def serializeFromScene(self, editorNode):
    state = UserStatisticsState(self, editorNode)
    state.populateFromScene()
    return state.serialize()

  def serializeFromTable(self, editorNode):
    state = UserStatisticsState(self, editorNode)
    state.populateFromTable()
    return state.serialize()

  def updateAllActiveRows(self, caller=None, event=None, callData=None):
    for editorNode in self.activeRows.keys():
      self.onEditorNodeModified(editorNode)

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
      tableNode.SetCellText(activeRow, column, self.getCurrentSceneStatus(editorNode, name))

  def setActiveRow(self, editorNode, row):
    if editorNode in self.activeRows:
      if self.activeRows[editorNode] == row:
        return
    self.updateActiveRow(editorNode, [self.DURATION_COLUMN_NAME])
    self.activeRows[editorNode] = row
    self.updateActiveRow(editorNode)

  def getCurrentTableText(self, editorNode, name):
    tableNode = self.getTimerTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(name))

  def getCurrentSceneStatus(self, editorNode, name):
    value = ""
    segmentationNode = editorNode.GetSegmentationNode()
    tableNode = self.getTimerTableNode()
    if tableNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow == -1:
      return ""

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
      value = tableNode.GetCellText(activeRow, tableNode.GetColumnIndex(name))
      if value == "":
        value = datetime.now().strftime(self.DATE_FORMAT)

    elif name == self.SCENE_COLUMN_NAME:
      value = slicer.mrmlScene.GetURL()

    elif name == self.SEGMENTATION_COLUMN_NAME:
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
      startTimeText = self.getCurrentTableText(editorNode, self.STARTTIME_COLUMN_NAME)
      if startTimeText == "":
        startTime = datetime.now()
      else:
        startTime = datetime.strptime(startTimeText, self.DATE_FORMAT)
      value = str((datetime.now() - startTime).total_seconds())

    elif name == self.MODULENAME_COLUMN_NAME:
      value = slicer.util.moduleSelector().selectedModule

    return value

  def setUserStatisticsTableNode(self, node):
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
    parameterNode.SetNodeReferenceID(self.USER_STATISTICS_TABLE_REFERENCE_ROLE, nodeID)

class UserStatisticsState():

  def __init__(self, logic, editorNode):
    self.logic = logic
    self.editorNode = editorNode

  parameters = {}
  ignoredParameters = [
    UserStatisticsLogic.DURATION_COLUMN_NAME,
    UserStatisticsLogic.STARTTIME_COLUMN_NAME,
  ]

  def populateFromScene(self):
    for name in UserStatisticsLogic.timerTableColumnNames:
      self.parameters[name] = self.logic.getCurrentSceneStatus(self.editorNode, name)

  def populateFromTable(self):
    for name in UserStatisticsLogic.timerTableColumnNames:
      self.parameters[name] = self.logic.getCurrentTableText(self.editorNode, name)

  def serialize(self):
    output = ""
    for name in self.parameters.keys():
      if name in self.ignoredParameters:
        continue
      value = self.parameters[name]
      output += str(value) + ","
    return output

class UserStatisticsTest(ScriptedLoadableModuleTest):
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
    self.test_UserStatistics1()

  def test_UserStatistics1(self):
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
