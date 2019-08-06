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

class SegmentationActiveState():
  segmentationNodeID = ""
  segmentID = ""
  activeEffect = ""
  terminology = ""

  def serialize(self):

    if self.segmentationNodeID == None:
      self.segmentationNodeID = ""
    if self.segmentID == None:
      self.segmentID = ""
    if self.activeEffect == None:
      self.activeEffect = ""
    if self.terminology == None:
      self.terminology = ""

    output = ""
    output += self.segmentationNodeID + ";"
    output += self.segmentID + ";"
    output += self.activeEffect + ";"
    output += self.terminology + ";"
    return output

#
# SegmentationTimerWidget
#

class SegmentationTimerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  DATE_FORMAT = "%m/%d/%Y, %H:%M:%S"
  COMPUTER_COLUMN = 0
  STARTTIME_COLUMN = 1
  SCENE_COLUMN = 2
  SEGMENTATION_COLUMN = 3
  SEGMENT_COLUMN = 4
  TERMINOLOGY_COLUMN = 5
  OPERATION_COLUMN = 6
  DURATION_COLUMN = 7
  LAST_COLUMN = 8
  timerTableColumnNames = []
  timerTableColumnTypes = {
    'computer': 'string',
    'starttime': 'string',
    'scene': 'string',
    'segmentation': 'string',
    'segment': 'string',
    'terminology': 'string',
    'operation': 'string',
    'duration': 'double'
  }
  activeRows = {}

  def __init__(self, parent):
    print("STARTING")
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.timerTableColumnNames = [None] * self.LAST_COLUMN
    self.timerTableColumnNames[self.COMPUTER_COLUMN] = 'computer'
    self.timerTableColumnNames[self.STARTTIME_COLUMN] = 'starttime'
    self.timerTableColumnNames[self.SCENE_COLUMN] = 'scene'
    self.timerTableColumnNames[self.SEGMENTATION_COLUMN] = 'segmentation'
    self.timerTableColumnNames[self.SEGMENT_COLUMN] = 'segment'
    self.timerTableColumnNames[self.TERMINOLOGY_COLUMN] = 'terminology'
    self.timerTableColumnNames[self.OPERATION_COLUMN] = 'operation'
    self.timerTableColumnNames[self.DURATION_COLUMN] = 'duration'

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/SegmentationTimer.ui'))
    self.layout.addWidget(uiWidget)

    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.selectSegmentationTimerTableNode()
    self.addSegmentEditorObservers()

    # connections

    # Add vertical spacer
    self.layout.addStretch(1)

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

  def cleanup(self):
    pass

  def onSceneStartClose(self, caller, event):
    pass

  def onSceneEndClose(self, caller, event):
    if self.parent.isEntered:
      self.selectSegmentationTimerTableNode()

  def onSceneEndImport(self, caller, event):
    if self.parent.isEntered:
      self.selectSegmentationTimerTableNode()

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
    tableNode = self.ui.statisticsTable.mrmlTableNode()
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

    activeState = SegmentationActiveState()
    if editorNode.GetSelectedSegmentID():
      activeState.segmentID = editorNode.GetSelectedSegmentID()
    segmentationNode = editorNode.GetSegmentationNode()
    if segmentationNode is not None:
      activeState.segmentationNodeID = segmentationNode.GetID()
      segmentation = segmentationNode.GetSegmentation()
      segment = segmentation.GetSegment(activeState.segmentID)
      if segment is not None:
        tag = vtk.mutable("")
        segment.GetTag(segment.GetTerminologyEntryTagName(), tag)
        activeState.terminology = tag.get()
    activeState.activeEffect = editorNode.GetActiveEffectName()
    return activeState.serialize()

  def serializeActiveRow(self, editorNode):
    if editorNode is None:
      return ""

    activeState = SegmentationActiveState()
    activeState.segmentID = self.getActiveSegmentID(editorNode)
    activeState.segmentationNodeID = self.getActiveSegmentationNodeID(editorNode)
    activeState.activeEffect = self.getActiveEditorEffect(editorNode)
    activeState.terminology = self.getActiveTerminology(editorNode)
    return activeState.serialize()

  def updateActiveRow(self, editorNode, columns=[]):
    if not editorNode in self.activeRows:
      return
    activeRow = self.activeRows[editorNode]
    if activeRow == -1:
      return

    tableNode = self.ui.statisticsTable.mrmlTableNode()
    for column in range(self.LAST_COLUMN):
      name = self.timerTableColumnNames[column]
      if columns != [] and not name in columns:
        continue
      value = ""
      if name == 'computer':
        hostInfo = qt.QHostInfo()
        value = hostInfo.localHostName()
      elif name == 'starttime':
        if tableNode.GetCellText(activeRow, self.STARTTIME_COLUMN) == "":
          value = datetime.now().strftime(self.DATE_FORMAT)
      elif name == 'scene':
        pass
      elif name == 'segmentation':
        segmentationNode = editorNode.GetSegmentationNode()
        if segmentationNode is not None:
          value = segmentationNode.GetID()
      elif name == 'segment':
        value = editorNode.GetSelectedSegmentID()
      elif name == 'terminology':
        if segmentationNode is not None:
          segmentation = segmentationNode.GetSegmentation()
          if editorNode.GetSelectedSegmentID():
            segment = segmentation.GetSegment(editorNode.GetSelectedSegmentID())
            if segment is not None:
              tag = vtk.mutable("")
              segment.GetTag(segment.GetTerminologyEntryTagName(), tag)
              value = tag.get()
      elif name == "operation":
        value = editorNode.GetActiveEffectName()
      elif name == 'duration':
        value = str((datetime.now() - self.getActiveStartTime(editorNode)).total_seconds())
      else:
        continue
      tableNode.SetCellText(activeRow, column, value)

  def setActiveRow(self, editorNode, row):
    if editorNode in self.activeRows:
      if self.activeRows == row:
        return
    self.updateActiveRow(editorNode, ["duration"])
    self.activeRows[editorNode] = row
    self.updateActiveRow(editorNode)

  def getActiveStartTime(self, editorNode):
    tableNode = self.ui.statisticsTable.mrmlTableNode()
    if tableNode is None or editorNode is None:
      return datetime.now()
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return datetime.now()
    startText = tableNode.GetCellText(activeRow, self.STARTTIME_COLUMN)
    if startText == "":
      return datetime.now()
    return datetime.strptime(startText, self.DATE_FORMAT)

  def getActiveEditorEffect(self, editorNode):
    tableNode = self.ui.statisticsTable.mrmlTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, self.OPERATION_COLUMN)

  def getActiveSegmentationNodeID(self, editorNode):
    tableNode = self.ui.statisticsTable.mrmlTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, self.SEGMENTATION_COLUMN)

  def getActiveSegmentID(self, editorNode):
    tableNode = self.ui.statisticsTable.mrmlTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, self.SEGMENT_COLUMN)

  def getActiveTerminology(self, editorNode):
    tableNode = self.ui.statisticsTable.mrmlTableNode()
    if tableNode is None or editorNode is None:
      return ""
    activeRow = self.activeRows[editorNode]
    if activeRow < 0:
      return ""
    return tableNode.GetCellText(activeRow, self.TERMINOLOGY_COLUMN)

  def selectSegmentationTimerTableNode(self):
    # Select parameter set node if one is found in the scene, and create one otherwise
    segmentationTimerSingletonTag = "SegmentationTimer.TableNode"
    timerTableNode = slicer.mrmlScene.GetSingletonNode(segmentationTimerSingletonTag, "vtkMRMLTableNode")
    if timerTableNode is None:
      timerTableNode = slicer.vtkMRMLTableNode()
      timerTableNode.SetName("SegmentationTimerNode")
      for columnIndex in range(self.LAST_COLUMN):
        name = self.timerTableColumnNames[columnIndex]
        type = self.timerTableColumnTypes[name]
        column = timerTableNode.AddColumn()
        column.SetName(name)
        column.SetName(name)
        timerTableNode.SetColumnProperty(name, "type", type)
      timerTableNode.SetUseFirstColumnAsRowHeader(False)
      timerTableNode.SetUseColumnNameAsColumnHeader(True)

      timerTableNode.SetSingletonTag(segmentationTimerSingletonTag)
      timerTableNode = slicer.mrmlScene.AddNode(timerTableNode)
    if self.ui.statisticsTable.mrmlTableNode() == timerTableNode:
      # nothing changed
      return
    self.ui.statisticsTable.setMRMLScene(slicer.mrmlScene)
    self.ui.statisticsTable.setMRMLTableNode(timerTableNode)

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
