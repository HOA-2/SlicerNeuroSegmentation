
import os
import unittest
import string
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging
import numpy as np

class CurveComparison(ScriptedLoadableModule, VTKObservationMixin):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.parent.title = "Curve Comparison"
    self.parent.categories = [""]
    self.parent.dependencies = []
    self.parent.contributors = [""]
    self.parent.helpText = """"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """"""

class CurveComparisonWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.logic = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/CurveComparison.ui'))
    uiWidget.setMRMLScene(slicer.mrmlScene)

    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.computeButton.connect('clicked(bool)', self.onComputeButtonClicked)

    self.logic = CurveComparisonLogic()

  def 

  def onComputeButtonClicked(self):
    inputCurveNode = self.ui.inputCurveNodeSelector.currentNode()
    outputTableNode = self.ui.outputTableNodeSelector.currentNode()
    self.logic.runCurveOptimization(inputCurveNode, outputTableNode)

    weight, distance = self.logic.getLowestAverageDistanceWeight(outputTableNode)
    self.ui.lowestAverageLineEdit.text = str(weight)

    weight, distance = self.logic.getLowestMaximumDistanceWeight(outputTableNode)
    self.ui.lowestMaxLineEdit.text = str(weight)

    weight, overlap = self.logic.getHightestOverlapPercentWeight(outputTableNode)
    self.ui.hightestOverlapLineEdit.text = str(weight)

class CurveComparisonMetrics():
  averageDistance = 0.0
  maxDistance = 0.0
  overlapPercent = 0.0
  weights = []

  def __init__(self, averageDistance, maxDistance, overlapPercent, weights):
    self.averageDistance = averageDistance
    self.maxDistance = maxDistance
    self.overlapPercent = overlapPercent
    self.weights = weights

class CurveComparisonLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):

  WEIGHTS_COLUMN_NAME = "Weights"
  AVERAGE_DISTANCE_COLUMN_NAME = "Average distance (mm)"
  MAX_DISTANCE_COLUMN_NAME = "Max distance (mm)"
  OVERLAP_PERCENT_COLUMN_NAME = "Overlap percent (%)"

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    VTKObservationMixin.__init__(self)
  
  def runCurveOptimization(self, inputCurveNode, outputTableNode):
    """
    :param inputCurveNode: User placed curve node to be optimized
    """
    metrics = []

    inputCurvePolyData = vtk.vtkPolyData()
    inputCurvePolyData.SetPoints(inputCurveNode.GetCurvePointsWorld())

    inputPointLocator = vtk.vtkPointLocator()
    inputPointLocator.SetDataSet(inputCurvePolyData)
    inputPointLocator.BuildLocator()

    weightArray = vtk.vtkStringArray()
    weightArray.SetName(self.WEIGHTS_COLUMN_NAME)

    averageDistanceArray = vtk.vtkDoubleArray()
    averageDistanceArray.SetName(self.AVERAGE_DISTANCE_COLUMN_NAME)

    maxDistanceArray = vtk.vtkDoubleArray()
    maxDistanceArray.SetName(self.MAX_DISTANCE_COLUMN_NAME)

    overlapPercentArray = vtk.vtkDoubleArray()
    overlapPercentArray.SetName(self.OVERLAP_PERCENT_COLUMN_NAME)

    table = vtk.vtkTable()
    table.AddColumn(weightArray)
    table.AddColumn(averageDistanceArray)
    table.AddColumn(maxDistanceArray)
    table.AddColumn(overlapPercentArray)
    outputTableNode.SetAndObserveTable(table)

    optimizerCurve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLFreeSurferMarkupsCurveNode")
    optimizerCurve.SetAndObserveShortestDistanceSurfaceNode(inputCurveNode.GetShortestDistanceSurfaceNode())
    optimizerCurve.SetCurveTypeToShortestDistanceOnSurface()

    numberOfControlPoints = inputCurveNode.GetNumberOfControlPoints()
    startPoint_World = [0,0,0]
    inputCurveNode.GetNthControlPointPositionWorld(0, startPoint_World)
    endPoint_World = [0,0,0]
    inputCurveNode.GetNthControlPointPositionWorld(numberOfControlPoints-1, endPoint_World )

    points = vtk.vtkPoints()
    points.InsertNextPoint(startPoint_World)
    points.InsertNextPoint(endPoint_World)
    optimizerCurve.SetControlPointPositionsWorld(points)

    for i in range(1, pow(2, 8)):
      weights = self.binaryArray(i, 8)
      self.evaluateWeights(inputCurveNode, optimizerCurve, weights, inputPointLocator, outputTableNode)
    table.Modified()

    slicer.mrmlScene.RemoveNode(optimizerCurve)

  def getLowestAverageDistanceWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    averageDistanceArray = tableNode.GetTable().GetColumnByName(self.AVERAGE_DISTANCE_COLUMN_NAME)

    lowestAverageDistanceIndex = -1
    lowestAverageDistance = vtk.VTK_DOUBLE_MAX
    for i in range(weightsArray.GetNumberOfValues()):
      average = averageDistanceArray.GetValue(i)
      if average < lowestAverageDistance:
        lowestAverageDistance = average
        lowestAverageDistanceIndex = i

    weight = weightsArray.GetValue(lowestAverageDistanceIndex)
    return weight, lowestAverageDistance

  def getLowestMaximumDistanceWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    maxDistanceArray = tableNode.GetTable().GetColumnByName(self.MAX_DISTANCE_COLUMN_NAME)

    lowestMaxDistanceIndex = -1
    lowestMaxDistance = vtk.VTK_DOUBLE_MAX
    for i in range(weightsArray.GetNumberOfValues()):
      maxDistance = maxDistanceArray.GetValue(i)
      if maxDistance < lowestMaxDistance:
        lowestMaxDistance = maxDistance
        lowestMaxDistanceIndex = i
    weight = weightsArray.GetValue(lowestMaxDistanceIndex)
    return weight, lowestMaxDistanceIndex


  def getHightestOverlapPercentWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    overlapPercentArray = tableNode.GetTable().GetColumnByName(self.OVERLAP_PERCENT_COLUMN_NAME)

    highestOverlapPercentIndex = -1
    highestOverlapPercent = 0.0
    for i in range(weightsArray.GetNumberOfValues()):
      overlapPercent = overlapPercentArray.GetValue(i)
      if overlapPercent > highestOverlapPercent:
        highestOverlapPercent = overlapPercent
        highestOverlapPercentIndex = i
    weight = weightsArray.GetValue(highestOverlapPercentIndex)
    return weight, highestOverlapPercent

  def evaluateWeights(self, inputCurveNode, optimizerCurveNode, weights, inputPointLocator, outputTableNode):
    # [d,   c,   h,  dc,  dh,  ch, dch,   p]
    optimizerCurveNode.SetDistanceWeight(weights[0])
    optimizerCurveNode.SetCurvatureWeight(weights[1])
    optimizerCurveNode.SetSulcalHeightWeight(weights[2])
    optimizerCurveNode.SetDistanceCurvatureWeight(weights[3])
    optimizerCurveNode.SetDistanceSulcalHeightWeight(weights[4])
    optimizerCurveNode.SetCurvatureSulcalHeightWeight(weights[5])
    optimizerCurveNode.SetDistanceCurvatureSulcalHeightWeight(weights[6])
    optimizerCurveNode.SetDirectionWeight(weights[7])

    optimizerPoints = optimizerCurveNode.GetCurvePointsWorld()
    averageDistance2 = 0.0
    maxDistance2 = 0.0
    overlapPercent = 0.0
    for i in range(optimizerPoints.GetNumberOfPoints()):
      optimizerPoint_World = optimizerPoints.GetPoint(i)
      closestInputPointID = inputPointLocator.FindClosestPoint(optimizerPoint_World)
      closestPoint_World = inputCurveNode.GetCurvePointsWorld().GetPoint(closestInputPointID)
      distance2 = vtk.vtkMath.Distance2BetweenPoints(optimizerPoint_World, closestPoint_World)
      averageDistance2 += (distance2/optimizerPoints.GetNumberOfPoints())
      if distance2 > maxDistance2:
        maxDistance2 = distance2
      if distance2 == 0.0:
        overlapPercent += 1.0 / optimizerPoints.GetNumberOfPoints()
    import math

    weightsArray = outputTableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    weightsArray.InsertNextValue(str(weights))

    averageDistanceArray = outputTableNode.GetTable().GetColumnByName(self.AVERAGE_DISTANCE_COLUMN_NAME)
    averageDistanceArray.InsertNextTuple1(math.sqrt(averageDistance2))

    maxDistanceArray = outputTableNode.GetTable().GetColumnByName(self.MAX_DISTANCE_COLUMN_NAME)
    maxDistanceArray.InsertNextTuple1(math.sqrt(maxDistance2))

    overlapPercentArray = outputTableNode.GetTable().GetColumnByName(self.OVERLAP_PERCENT_COLUMN_NAME)
    overlapPercentArray.InsertNextTuple1(overlapPercent)

  def binaryArray(self, num, m):
    """
    Convert a positive integer num into an m-bit bit vector
    From: https://stackoverflow.com/a/47521145
    """
    return np.array(list(np.binary_repr(num).zfill(m))).astype(np.int8)
    
