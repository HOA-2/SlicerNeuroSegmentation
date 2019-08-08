import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin, NodeModify
from datetime import datetime, timedelta

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

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/UserStatistics.ui'))
    self.layout.addWidget(uiWidget)

    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.tableNodeSelector.addAttribute("vtkMRMLTableNode", "UserStatistics.TableNode", "")
    self.ui.mergeTablesNodeSelector.addAttribute("vtkMRMLTableNode", "UserStatistics.TableNode", "")
    self.ui.userStatistics.setMRMLScene(slicer.mrmlScene)

    # Connections
    self.ui.tableNodeSelector.nodeAddedByUser.connect(self.onNodeAddedByUser)
    self.ui.tableNodeSelector.currentNodeChanged.connect(self.onCurrentNodeChanged)
    self.ui.mergeTablesButton.clicked.connect(self.onMergeStatisticTablesClicked)

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartImportEvent, self.onSceneStartImport)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)

    self.sceneClosedTimer = qt.QTimer()
    self.sceneClosedTimer.setInterval(1)
    self.sceneClosedTimer.setSingleShot(True)
    self.sceneClosedTimer.timeout.connect(self.onSceneClosed)

    self.sceneImportTimer = qt.QTimer()
    self.sceneImportTimer.setInterval(1)
    self.sceneImportTimer.setSingleShot(True)
    self.sceneImportTimer.timeout.connect(self.onSceneImport)

    self.importInProgress = False

    self.idleDetectionEventFilter = IdleDetectionEventFilter()
    self.idleDetectionEventFilter.setInterval(self.logic.IDLE_TIMEOUT_SECONDS * 1000)
    slicer.app.installEventFilter(self.idleDetectionEventFilter)
    self.idleDetectionEventFilter.idleStarted.connect(self.onIdleStarted)
    self.idleDetectionEventFilter.idleEnded.connect(self.onIdleEnded)
    self.idleDetectionEventFilter.start()
    self.idleDetectionEventFilter.deleteLater()

    # This will use createParameterNode with the provided default options
    self.setParameterNode(self.logic.getParameterNode())

  def onSceneStartClose(self, caller, event):
    self.setParameterNode(None)

  def onSceneEndClose(self, caller=None, event=None):
    self.sceneClosedTimer.start()

  def onSceneClosed(self, caller=None, event=None):
    self.logic.onSceneEndClose()
    self.setParameterNode(self.logic.getParameterNode())

  def onSceneStartImport(self, caller, event):
    self.importInProgress = True
    self.logic.onSceneStartImport()

  def onSceneEndImport(self, caller, event):
    self.sceneImportTimer.start()

  def onSceneImport(self, caller=None, event=None):
    self.importInProgress = False
    self.logic.onSceneEndImport()
    self.updateGuiFromMRML()

  def onIdleStarted(self):
    self.logic.onIdleStarted()

  def onIdleEnded(self):
    self.logic.onIdleEnded()

  def cleanup(self):
    pass

  def onNodeAddedByUser(self, node):
    self.logic.setupTimerTableNode(node)

  def onCurrentNodeChanged(self, node):
    if self.importInProgress:
      return
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
    self.updateGuiFromMRML()

  def updateGuiFromMRML(self, caller=None, event=None, callData=None):
    currentNode = self.logic.getUserStatisticsTableNode()
    selectedNode = self.ui.tableNodeSelector.currentNode()
    if not currentNode is selectedNode:
      self.ui.tableNodeSelector.setCurrentNode(currentNode)

class UserStatisticsLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):

  USER_STATISTICS_TABLE_REFERENCE_ROLE = "userStatisticsTableRef"

  DATE_FORMAT = "%Y%m%d-%H%M%S"

  COMPUTER_COLUMN_NAME = 'computer'
  USER_NAME_COLUMN_NAME = 'userName'
  MASTER_VOLUME_NAME_COLUMN_NAME = 'masterVolumeName'
  START_TIME_COLUMN_NAME = 'startTime'
  SCENE_COLUMN_NAME = 'scene'
  SEGMENTATION_NAME_COLUMN_NAME = 'segmentationName'
  SEGMENT_NAME_COLUMN_NAME = 'segmentName'
  TERMINOLOGY_COLUMN_NAME = 'segmentTerminology'
  MODULE_NAME_COLUMN_NAME = 'moduleName'
  OPERATION_COLUMN_NAME = 'operation'
  USER_ACTIVITY_COLUMN_NAME = 'userActivity'
  DURATION_COLUMN_NAME = 'durationSec'

  timerTableColumnNames = [
    START_TIME_COLUMN_NAME,
    OPERATION_COLUMN_NAME,
    DURATION_COLUMN_NAME,
    SEGMENT_NAME_COLUMN_NAME,
    MASTER_VOLUME_NAME_COLUMN_NAME,
    SEGMENTATION_NAME_COLUMN_NAME,
    TERMINOLOGY_COLUMN_NAME,
    MODULE_NAME_COLUMN_NAME,
    USER_ACTIVITY_COLUMN_NAME,
    COMPUTER_COLUMN_NAME,
    USER_NAME_COLUMN_NAME,
    SCENE_COLUMN_NAME,
  ]

  serializedParameters = [
    OPERATION_COLUMN_NAME,
    SEGMENT_NAME_COLUMN_NAME,
    MASTER_VOLUME_NAME_COLUMN_NAME,
    SEGMENTATION_NAME_COLUMN_NAME,
    TERMINOLOGY_COLUMN_NAME,
    MODULE_NAME_COLUMN_NAME,
    USER_ACTIVITY_COLUMN_NAME,
    COMPUTER_COLUMN_NAME,
    USER_NAME_COLUMN_NAME,
    SCENE_COLUMN_NAME,
  ]

  ACTIVITY_ACTIVE = "active"
  ACTIVITY_WAIT = "wait"
  ACTIVITY_IDLE = "idle"

  WAIT_TIMEOUT_SECONDS = 1.0
  WAIT_TIMEOUT_THRESHOLD_SECONDS = 1.1 * WAIT_TIMEOUT_SECONDS
  IDLE_TIMEOUT_SECONDS = 30.0

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    VTKObservationMixin.__init__(self)

    self.timerTableColumnTypes = {}
    for name in self.timerTableColumnNames:
      if name == self.DURATION_COLUMN_NAME:
        self.timerTableColumnTypes[name] = 'double'
      else:
        self.timerTableColumnTypes[name] = 'string'

    self.editorNode = None
    self.userActivity = self.ACTIVITY_ACTIVE
    self.importInProgress = False

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

    self.addSegmentEditorObservers()

    slicer.util.moduleSelector().moduleSelected.connect(self.updateTable)

    self.waitDetectionLastTimeout = vtk.vtkTimerLog.GetUniversalTime()
    self.waitDetectionTimer = qt.QTimer()
    self.waitDetectionTimer.setInterval(self.WAIT_TIMEOUT_SECONDS * 1000)
    self.waitDetectionTimer.setSingleShot(False)
    self.waitDetectionTimer.timeout.connect(self.onWaitDetectionTimer)
    self.waitDetectionTimer.start()

    self.getUserStatisticsTableNode()

  def onSceneClosed(self):
    self.getUserStatisticsTableNode()
    self.updateTable()

  def onWaitDetectionTimer(self):
    oldTime = self.waitDetectionLastTimeout
    self.waitDetectionLastTimeout = vtk.vtkTimerLog.GetUniversalTime()
    waitLength = self.waitDetectionLastTimeout - oldTime
    if waitLength > self.WAIT_TIMEOUT_THRESHOLD_SECONDS:
      self.onWaitDetected(waitLength)

  def onWaitDetected(self, length):
    if self.importInProgress:
      return
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return

    oldRow = self.getActiveRow()
    self.userActivity = self.ACTIVITY_WAIT
    self.updateTable()
    waitRow = self.getActiveRow()
    self.userActivity = self.ACTIVITY_ACTIVE
    self.updateTable()

    if oldRow > -1:
      # Update duration in old active row
      oldRowDuration = self.getDurationForRow(oldRow) - length
      self.setDurationForRow(oldRow, oldRowDuration)
      # Update start time in the new wait row
      startTimeColumnIndex = tableNode.GetColumnIndex(self.START_TIME_COLUMN_NAME)
      oldStartTimeText = tableNode.GetCellText(oldRow, startTimeColumnIndex)
      oldStartTime = datetime.strptime(oldStartTimeText, self.DATE_FORMAT)
      oldStartTime += timedelta(seconds=oldRowDuration)
      tableNode.SetCellText(waitRow, startTimeColumnIndex, oldStartTime.strftime(self.DATE_FORMAT))
    # Update duration in the new active row
    self.setDurationForRow(waitRow, length)

  def onIdleStarted(self):
    if self.importInProgress:
      return
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return

    oldRow = self.getActiveRow()
    self.userActivity = self.ACTIVITY_IDLE
    self.updateTable()
    idleRow = self.getActiveRow()
    if oldRow > -1:
      oldRowDuration = self.getDurationForRow(oldRow) - self.IDLE_TIMEOUT_SECONDS
      self.setDurationForRow(oldRow, oldRowDuration)
      startTimeColumnIndex = tableNode.GetColumnIndex(self.START_TIME_COLUMN_NAME)
      oldStartTimeText = tableNode.GetCellText(oldRow, startTimeColumnIndex)
      oldStartTime = datetime.strptime(oldStartTimeText, self.DATE_FORMAT)
      oldStartTime += timedelta(seconds=oldRowDuration)
      tableNode.SetCellText(idleRow, startTimeColumnIndex, oldStartTime.strftime(self.DATE_FORMAT))

  def onIdleEnded(self):
    self.userActivity = self.ACTIVITY_ACTIVE
    self.updateTable()

  def onSceneEndClose(self, caller=None, event=None):
    self.getUserStatisticsTableNode()
    self.updateTable()

  def onSceneStartImport(self, caller=None, event=None):
    self.importInProgress = True

  def onSceneEndImport(self, caller=None, event=None):
    self.importInProgress = False

  def getActiveRow(self):
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return -1
    return tableNode.GetNumberOfRows() - 1

  def mergeStatisticsTableNodes(self, tableNodes):
    if len(tableNodes) < 2:
      return

    currentRowIndexes = {}
    for tableNode in tableNodes:
      currentRowIndexes[tableNode] = 0

    newTableNode = slicer.vtkMRMLTableNode()
    newTableNode.SetName("UserStatisticsTableNode")
    newTableNode.SetAttribute("UserStatistics.TableNode", "")
    self.setupTimerTableNode(newTableNode)

    completed = False
    while not completed:
      rows = {}

      # Popupulate the list of rows starting at the top of each table and moving down
      for tableNode in tableNodes:
        currentIndex = currentRowIndexes[tableNode]
        if currentIndex < tableNode.GetNumberOfRows():
          row = vtk.vtkVariantArray()
          tableNode.GetTable().GetRow(currentIndex, row)
          rows[tableNode] = row

      # Done! There are no more rows left in any of the tables
      if rows == {}:
        completed = True
      else:
        # Find the "minimum" row by comparing the string format contents of all rows
        nodeForRow = None
        rowToAdd = None
        rowToAddString = None
        for tableNode in rows.keys():
          row = rows[tableNode]
          rowString = self.variantArrayToString(row)

          # This row is the new "minimum" row to be added to the table next
          if rowToAdd is None or rowString < rowToAddString:
            nodeForRow = tableNode
            rowToAdd = row
            rowToAddString = rowString

          # This row is the same as the current "minimum". It is a duplicate so discard it
          elif rowString == rowToAddString:
            currentRowIndexes[tableNode] += 1

        # Add the "minimum" row and increment the index of the corresponding table node
        currentRowIndexes[nodeForRow] += 1
        newTableNode.GetTable().InsertNextRow(rowToAdd)
        newTableNode.GetTable().Modified()

    slicer.mrmlScene.AddNode(newTableNode)
    for tableNode in tableNodes:
      slicer.mrmlScene.RemoveNode(tableNode)

  def variantArrayToString(self, array):
    if array is None:
      return ""
    output = ""
    for i in range(array.GetNumberOfValues()):
      variant = array.GetValue(i)
      output += variant.ToString()
    return output

  def getUserStatisticsTableNode(self):
    parameterNode = self.getParameterNode()
    if parameterNode is None:
      return

    tableNode = parameterNode.GetNodeReference(self.USER_STATISTICS_TABLE_REFERENCE_ROLE)
    if not tableNode is None:
      return tableNode

    tableNodes = slicer.util.getNodesByClass("vtkMRMLTableNode")
    for node in tableNodes:
      if node.GetAttribute("UserStatistics.TableNode"):
        tableNode = node
        break

    if tableNode is None:
      tableNode = slicer.vtkMRMLTableNode()
      tableNode.SetName("UserStatisticsTableNode")
      tableNode.SetAttribute("UserStatistics.TableNode", "")
      slicer.mrmlScene.AddNode(tableNode)
      self.setupTimerTableNode(tableNode)
    self.setUserStatisticsTableNode(tableNode)
    return tableNode

  def setUserStatisticsTableNode(self, node):
    parameterNode = self.getParameterNode()
    if parameterNode is None:
      return

    with NodeModify(parameterNode):
      tableNode = parameterNode.GetNodeReference(self.USER_STATISTICS_TABLE_REFERENCE_ROLE)
      if node is tableNode:
        return

      nodeID = ""
      if node:
        nodeID = node.GetID()
      parameterNode.SetNodeReferenceID(self.USER_STATISTICS_TABLE_REFERENCE_ROLE, nodeID)

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
    tableNode.SetLocked(True)

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
    self.editorNode = editorNode
    self.updateTable()

  def updateTable(self):
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return

    serializedScene = self.serializeFromScene()
    serializedTable = self.serializeFromTable()
    if self.getActiveRow() == -1 or serializedScene != serializedTable:
      self.updateActiveRow([self.DURATION_COLUMN_NAME])
      row = tableNode.AddEmptyRow()
      self.updateActiveRow()

  def serializeFromScene(self):
    output = ""
    for name in self.serializedParameters:
      value = self.getCurrentSceneStatus(name)
      output += str(value) + ","
    return output

  def serializeFromTable(self):
    output = ""
    for name in self.serializedParameters:
      value = self.getActiveTableText(name)
      output += str(value) + ","
    return output

  def updateActiveRow(self, columnsToUpdate=[], columnsToIgnore=[]):
    tableNode = self.getUserStatisticsTableNode()
    if self.getActiveRow() == -1 or tableNode is None:
      return

    for column in range(tableNode.GetNumberOfColumns()):
      name = tableNode.GetColumnName(column)
      if columnsToUpdate != [] and not name in columnsToUpdate:
        continue
      if name in columnsToIgnore:
        continue
      tableNode.SetCellText(self.getActiveRow(), column, self.getCurrentSceneStatus(name))

  def getDurationForRow(self, row):
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return 0.0
    return float(tableNode.GetCellText(row, tableNode.GetColumnIndex(self.DURATION_COLUMN_NAME)))

  def setDurationForRow(self, row, duration):
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return
    tableNode.SetCellText(row, tableNode.GetColumnIndex(self.DURATION_COLUMN_NAME), str(duration))

  def getActiveTableText(self, name):
    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return ""
    if self.getActiveRow() < 0:
      return ""
    return tableNode.GetCellText(self.getActiveRow(), tableNode.GetColumnIndex(name))

  def getCurrentSceneStatus(self, name):

    tableNode = self.getUserStatisticsTableNode()
    if tableNode is None:
      return ""
    if self.getActiveRow() == -1:
      return ""

    value = ""

    if name == self.COMPUTER_COLUMN_NAME:
      hostInfo = qt.QHostInfo()
      value = hostInfo.localHostName()

    elif name == self.USER_NAME_COLUMN_NAME:
      userInfo = slicer.app.applicationLogic().GetUserInformation()
      value = userInfo.GetName()

    elif name == self.MASTER_VOLUME_NAME_COLUMN_NAME:
      masterVolume = self.getMasterVolumeNode()
      if masterVolume:
        value = masterVolume.GetName()

    elif name == self.START_TIME_COLUMN_NAME:
      value = tableNode.GetCellText(self.getActiveRow(), tableNode.GetColumnIndex(name))
      if value == "":
        value = datetime.now().strftime(self.DATE_FORMAT)

    elif name == self.SCENE_COLUMN_NAME:
      value = slicer.mrmlScene.GetURL()

    elif name == self.SEGMENTATION_NAME_COLUMN_NAME:
      segmentationNode = self.getSegmentationNode()
      if segmentationNode is not None:
        value = segmentationNode.GetName()

    elif name == self.SEGMENT_NAME_COLUMN_NAME:
      segment = self.getSelectedSegment()
      if segment:
        value = segment.GetName()

    elif name == self.TERMINOLOGY_COLUMN_NAME:
      segment = self.getSelectedSegment()
      if segment is not None:
        tag = vtk.mutable("")
        segment.GetTag(segment.GetTerminologyEntryTagName(), tag)
        value = tag.get()

    elif name == self.OPERATION_COLUMN_NAME:
      if self.editorNode:
        value = self.editorNode.GetActiveEffectName()

    elif name == self.DURATION_COLUMN_NAME:
      startTimeText = self.getActiveTableText(self.START_TIME_COLUMN_NAME)
      if startTimeText == "":
        startTime = datetime.now()
      else:
        startTime = datetime.strptime(startTimeText, self.DATE_FORMAT)
      value = str((datetime.now() - startTime).total_seconds())

    elif name == self.MODULE_NAME_COLUMN_NAME:
      value = slicer.util.moduleSelector().selectedModule

    elif name == self.USER_ACTIVITY_COLUMN_NAME:
      value = self.userActivity

    return value

  def getSegmentationNode(self):
    if self.editorNode is None:
      return None
    return self.editorNode.GetSegmentationNode()

  def getMasterVolumeNode(self):
    if self.editorNode is None:
      return None
    return self.editorNode.GetMasterVolumeNode()

  def getSelectedSegment(self):
    if self.editorNode is None:
      return None

    segmentationNode = self.getSegmentationNode()
    if segmentationNode is None:
      return None

    segmentation = segmentationNode.GetSegmentation()
    if segmentation is None:
      return None

    segmentID = self.editorNode.GetSelectedSegmentID()
    if segmentID is None or segmentID == "":
      return None

    return segmentation.GetSegment(segmentID)

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

class IdleDetectionEventFilter(qt.QObject):

  idleTimeoutSeconds = 30
  idleStarted = qt.Signal()
  idleEnded = qt.Signal()

  events = [
    qt.QEvent.MouseMove,
    qt.QEvent.KeyPress,
  ]

  def __init__(self):
    qt.QObject.__init__(self)

    self.idleTimer = qt.QTimer()
    self.idleTimer.setSingleShot(True)
    self.idleTimer.timeout.connect(self.onIdleStarted)
    self.idling = False

  def setInterval(self, interval):
    self.idleTimer.setInterval(interval)

  def start(self):
    self.idleTimer.start()

  def eventFilter(self, object, event):
    if event.type() in self.events:
      self.idleTimer.start()
      if self.idling:
        self.idling = False
        self.onIdleEnded()
    return False

  def onIdleStarted(self):
    self.idleStarted.emit()
    self.idling = True

  def onIdleEnded(self):
    self.idleEnded.emit()
