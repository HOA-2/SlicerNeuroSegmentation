
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

    weight, overlap = self.logic.getHightestISOOverlapWeight(outputTableNode)
    self.ui.hightestISOOverlapLineEdit.text = str(weight)

class CurveComparisonLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):

  WEIGHTS_COLUMN_NAME = "Weights"
  AVERAGE_DISTANCE_COLUMN_NAME = "Average distance (mm)"
  MAX_DISTANCE_COLUMN_NAME = "Max distance (mm)"
  OVERLAP_PERCENT_COLUMN_NAME = "Overlap percent (%)"
  ISO_OVERLAP_COLUMN_NAME = "ISO overlap"

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

    inputPolyDataLocator = vtk.vtkPointLocator()
    inputPolyDataLocator.SetDataSet(inputCurveNode.GetShortestDistanceSurfaceNode().GetPolyData())
    inputPolyDataLocator.BuildLocator()

    self.createISORegionOverlay(inputCurveNode)

    weightArray = vtk.vtkStringArray()
    weightArray.SetName(self.WEIGHTS_COLUMN_NAME)

    averageDistanceArray = vtk.vtkDoubleArray()
    averageDistanceArray.SetName(self.AVERAGE_DISTANCE_COLUMN_NAME)

    maxDistanceArray = vtk.vtkDoubleArray()
    maxDistanceArray.SetName(self.MAX_DISTANCE_COLUMN_NAME)

    overlapPercentArray = vtk.vtkDoubleArray()
    overlapPercentArray.SetName(self.OVERLAP_PERCENT_COLUMN_NAME)

    isoOverlapArray = vtk.vtkDoubleArray()
    isoOverlapArray.SetName(self.ISO_OVERLAP_COLUMN_NAME)

    

    table = vtk.vtkTable()
    table.AddColumn(weightArray)
    table.AddColumn(averageDistanceArray)
    table.AddColumn(maxDistanceArray)
    table.AddColumn(overlapPercentArray)
    table.AddColumn(isoOverlapArray)
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
      self.evaluateWeights(inputCurveNode, optimizerCurve, weights, inputPointLocator, inputPolyDataLocator, outputTableNode)
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
    highestOverlapPercent = vtk.VTK_DOUBLE_MIN
    for i in range(weightsArray.GetNumberOfValues()):
      overlapPercent = overlapPercentArray.GetValue(i)
      if overlapPercent > highestOverlapPercent:
        highestOverlapPercent = overlapPercent
        highestOverlapPercentIndex = i
    weight = weightsArray.GetValue(highestOverlapPercentIndex)
    return weight, highestOverlapPercent

  def getHightestISOOverlapWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    isoOverlapArray = tableNode.GetTable().GetColumnByName(self.ISO_OVERLAP_COLUMN_NAME)

    highestISOOverlapIndex = -1
    highestISOOverlap = vtk.VTK_DOUBLE_MIN
    for i in range(weightsArray.GetNumberOfValues()):
      isoOverlap = isoOverlapArray.GetValue(i)
      if isoOverlap > highestISOOverlap:
        highestISOOverlap = isoOverlap
        highestISOOverlapIndex = i
    weight = weightsArray.GetValue(highestISOOverlapIndex)
    return weight, highestISOOverlap

  def evaluateWeights(self, inputCurveNode, optimizerCurveNode, weights, inputCurveLocator, inputPolyDataLocator, outputTableNode):
    # [d,   c,   h,  dc,  dh,  ch, dch,   p]
    optimizerCurveNode.SetDistanceWeight(weights[0])
    optimizerCurveNode.SetCurvatureWeight(weights[1])
    optimizerCurveNode.SetSulcalHeightWeight(weights[2])
    optimizerCurveNode.SetDistanceCurvatureWeight(weights[3])
    optimizerCurveNode.SetDistanceSulcalHeightWeight(weights[4])
    optimizerCurveNode.SetCurvatureSulcalHeightWeight(weights[5])
    optimizerCurveNode.SetDistanceCurvatureSulcalHeightWeight(weights[6])
    optimizerCurveNode.SetDirectionWeight(weights[7])

    polyData = inputCurveNode.GetShortestDistanceSurfaceNode().GetPolyData()
    isoRegionsArrayName = "ISO-Regions"
    pointData = polyData.GetPointData()
    isoRegionsArray = pointData.GetArray(isoRegionsArrayName)

    isoRegionSum = {}

    optimizerPoints = optimizerCurveNode.GetCurvePointsWorld()
    averageDistance2 = 0.0
    maxDistance2 = 0.0
    overlapPercent = 0.0
    for i in range(optimizerPoints.GetNumberOfPoints()):
      optimizerPoint_World = optimizerPoints.GetPoint(i)
      closestInputPointID = inputCurveLocator.FindClosestPoint(optimizerPoint_World)
      closestPoint_World = inputCurveNode.GetCurvePointsWorld().GetPoint(closestInputPointID)
      distance2 = vtk.vtkMath.Distance2BetweenPoints(optimizerPoint_World, closestPoint_World)
      averageDistance2 += (distance2/optimizerPoints.GetNumberOfPoints())
      if distance2 > maxDistance2:
        maxDistance2 = distance2
      if distance2 == 0.0:
        overlapPercent += 1.0 / optimizerPoints.GetNumberOfPoints()

      polyDataPointID = inputPolyDataLocator.FindClosestPoint(optimizerPoint_World)
      isoRegion = isoRegionsArray.GetValue(polyDataPointID)
      if isoRegion >= 0:
        isoRegion = max(1, isoRegion)
        isoRegionSum[isoRegion] = isoRegionSum.get(isoRegion, 0) + 1

    import math

    weightsArray = outputTableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    weightsArray.InsertNextValue(str(weights))

    averageDistanceArray = outputTableNode.GetTable().GetColumnByName(self.AVERAGE_DISTANCE_COLUMN_NAME)
    averageDistanceArray.InsertNextTuple1(math.sqrt(averageDistance2))

    maxDistanceArray = outputTableNode.GetTable().GetColumnByName(self.MAX_DISTANCE_COLUMN_NAME)
    maxDistanceArray.InsertNextTuple1(math.sqrt(maxDistance2))

    overlapPercentArray = outputTableNode.GetTable().GetColumnByName(self.OVERLAP_PERCENT_COLUMN_NAME)
    overlapPercentArray.InsertNextTuple1(overlapPercent)

    isoOverlap = 0.0
    for isoRegion, regionSum in isoRegionSum.items():
      fr = regionSum / optimizerPoints.GetNumberOfPoints()
      penalty = -0.2
      isoOverlap += (1 - (fr * (1 + (penalty * (isoRegion - 1)))))
    isoOverlap /= 6
    isoOverlapArray = outputTableNode.GetTable().GetColumnByName(self.ISO_OVERLAP_COLUMN_NAME)
    isoOverlapArray.InsertNextTuple1(isoOverlap)
      

  def createISORegionOverlay(self, curveNode):
    """
    :param curve: The curve that the overlay will be created from (vtkMRMLMarkupsCurveNode)
    """
    polyData = curveNode.GetShortestDistanceSurfaceNode().GetPolyData()
    if polyData is None:
      #TODO
      return

    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(polyData)
    pointLocator.BuildLocator()

    curvePoints = curveNode.GetCurvePointsWorld()

    isoRegionsArrayName = "ISO-Regions"
    pointData = polyData.GetPointData()
    isoRegionsArray = pointData.GetArray(isoRegionsArrayName)
    if isoRegionsArray  is None:
      isoRegionsArray = vtk.vtkIdTypeArray()
      isoRegionsArray.SetName(isoRegionsArrayName)
    isoRegionsArray.SetNumberOfValues(polyData.GetNumberOfPoints())
    isoRegionsArray.Fill(-1)
    curveNode.GetShortestDistanceSurfaceNode().AddPointScalars(isoRegionsArray)

    visitedPoints = []
    previousISORegion = []
    for regionIndex in range(7):
      currentISORegion = []
      if regionIndex == 0:
        for i in range(curvePoints.GetNumberOfPoints()):
          curvePoint_World = curvePoints.GetPoint(i)
          currentISORegion.append(pointLocator.FindClosestPoint(curvePoint_World))
      else:      
        currentISORegion = self.getAdjacentPoints(polyData, previousISORegion)

      for isoPointID in currentISORegion:
        if isoPointID in visitedPoints:
          continue
        isoRegionsArray.SetValue(isoPointID, regionIndex)

      visitedPoints += currentISORegion
      previousISORegion = currentISORegion

  def getAdjacentPoints(self, inputPolydata, inputPointIDs):
    pointIDs = []
    cellIdList = vtk.vtkIdList()
    pointIdList = vtk.vtkIdList()
    for pointID in inputPointIDs:
      inputPolydata.GetPointCells(pointID, cellIdList)
      for cellIndex in range(cellIdList.GetNumberOfIds()):
        inputPolydata.GetCellPoints(cellIdList.GetId(cellIndex), pointIdList)
        for pointIndex in range(pointIdList.GetNumberOfIds()):
          pointID = pointIdList.GetId(pointIndex)
          if pointID in inputPointIDs or pointID in pointIDs:
            continue
          pointIDs.append(pointID)
    return pointIDs

  def binaryArray(self, num, m):
    """
    Convert a positive integer num into an m-bit bit vector
    From: https://stackoverflow.com/a/47521145
    """
    return np.array(list(np.binary_repr(num).zfill(m))).astype(np.int8)
    
