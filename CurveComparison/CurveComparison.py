
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
    self.parent.categories = ["Neuro Segmentation"]
    self.parent.dependencies = ["FreeSurferMarkups"]
    self.parent.contributors = ["Kyle Sunderland (Perk Lab, Queen's University)"]
    self.parent.helpText = """
This module will calculate the optimal parameters for NeuroSegment curve pathfinding based on an input curve that represents the ground truth.
""" # TODO: Add more documentation on the method used for pathfinding + optimization
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Kyle Sunderland (Perk Lab, Queen's University), and was partially funded by Brigham and Women's Hospital through NIH grant R01MH112748
"""

class CurveComparisonWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.logic = None
    self.previousScalarArrayName = ""
    self.previousArrayLocation = vtk.vtkDataObject.POINT
    self.previousColorNode = None
    self.previousAutoScalarRangeSetting = False
    self.previousScalarRange = (0.0, 1.0)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = CurveComparisonLogic()

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/CurveComparison.ui'))
    uiWidget.setMRMLScene(slicer.mrmlScene)

    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.computeButton.connect('clicked(bool)', self.onComputeButtonClicked)

    self.ui.inputCurveNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.inputCurveNodeChanged)
    self.ui.surfaceNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.surfaceNodeChanged)

    self.ui.showOverlayCheckBox.connect('clicked()', self.onShowOverlayClicked)

    self.ui.outputTableNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateWidgetFromMRML)

    self.updateWidgetFromMRML()

  def inputCurveNodeChanged(self):
    self.updateWidgetFromMRML()

  def surfaceNodeChanged(self):
    surfaceNode = self.ui.surfaceNodeSelector.currentNode()
    currentCurveNode = self.ui.inputCurveNodeSelector.currentNode()
    if currentCurveNode:
      currentCurveNode.SetAndObserveSurfaceConstraintNode(surfaceNode)
      currentCurveNode.SetCurveTypeToShortestDistanceOnSurface()
    self.updateWidgetFromMRML()

  def onShowOverlayClicked(self):
    surfaceNode = self.ui.surfaceNodeSelector.currentNode()
    if surfaceNode is None:
      return
    surfaceNode.CreateDefaultDisplayNodes()
    displayNode = surfaceNode.GetDisplayNode()

    colorNode = self.previousColorNode
    autoScalarRange = self.previousAutoScalarRangeSetting
    activeScalarName = self.previousScalarArrayName
    activeScalarLocation = self.previousArrayLocation
    scalarRange = self.previousScalarRange

    if self.ui.showOverlayCheckBox.checked:
      self.previousScalarArrayName = displayNode.GetActiveScalarName()
      self.previousArrayLocation = displayNode.GetActiveAttributeLocation()
      self.previousColorNode = displayNode.GetColorNode()
      self.previousAutoScalarRangeSetting = displayNode.GetAutoScalarRange()
      self.previousScalarRange = displayNode.GetScalarRange()
      activeScalarName = self.logic.ISO_REGIONS_ARRAY_NAME
      activeScalarLocation = vtk.vtkDataObject.POINT
      displayNode.SetActiveScalar(self.logic.ISO_REGIONS_ARRAY_NAME, vtk.vtkDataObject.POINT)
      scalarRange = [0.0, 1.0]
      autoScalarRange = True
      colorNode = slicer.util.getNode("ColdToHotRainbow")

    displayNode.AutoScalarRangeOff()
    displayNode.SetActiveScalar(activeScalarName, activeScalarLocation)
    displayNode.SetAndObserveColorNodeID(colorNode.GetID())
    displayNode.SetScalarRange(scalarRange)
    displayNode.SetAutoScalarRange(autoScalarRange)

    self.updateWidgetFromMRML()

  def updateWidgetFromMRML(self):
    # TODO: Parameter node
    currentCurveNode = self.ui.inputCurveNodeSelector.currentNode()
    surfaceNode = None
    if currentCurveNode:
      surfaceNode = currentCurveNode.GetSurfaceConstraintNode()
    currentTableNode = self.ui.outputTableNodeSelector.currentNode()

    wasBlocking  = self.ui.surfaceNodeSelector.blockSignals(True)
    self.ui.surfaceNodeSelector.setCurrentNode(surfaceNode)
    self.ui.surfaceNodeSelector.blockSignals(wasBlocking)

    activeName = ""
    surfaceNode = self.ui.surfaceNodeSelector.currentNode()
    if surfaceNode and surfaceNode.GetDisplayNode():
      activeName = surfaceNode.GetDisplayNode().GetActiveScalarName()
    self.ui.showOverlayCheckBox.checked = (activeName == self.logic.ISO_REGIONS_ARRAY_NAME)
    self.ui.showOverlayCheckBox.enabled = not surfaceNode is None

    self.ui.computeButton.enabled = (not currentTableNode is None and not currentCurveNode is None and
      not currentCurveNode.GetShortestDistanceSurfaceNode() is None and currentCurveNode.GetNumberOfControlPoints() >= 2)

  def onComputeButtonClicked(self):
    try:
      qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
      slicer.app.pauseRender()
      inputCurveNode = self.ui.inputCurveNodeSelector.currentNode()
      outputTableNode = self.ui.outputTableNodeSelector.currentNode()
      self.logic.runCurveOptimization(inputCurveNode, outputTableNode)

      weight, distance = self.logic.getLowestAverageDistanceWeight(outputTableNode)
      self.ui.lowestAverageLineEdit.text = str(weight)

      weight, distance = self.logic.getLowestMaximumDistanceWeight(outputTableNode)
      self.ui.lowestMaxLineEdit.text = str(weight)

      weight, overlap = self.logic.getHighestOverlapPercentWeight(outputTableNode)
      self.ui.highestOverlapLineEdit.text = str(weight)

      weight, overlap = self.logic.getHighestISOOverlapWeight(outputTableNode)
      self.ui.highestISOOverlapLineEdit.text = str(weight)

      optimizerCurve = slicer.mrmlScene.GetFirstNodeByName("CurveComparisonPreview")
      import json
      weight = json.loads(weight)
      self.logic.setCurveNodeWeights(optimizerCurve, weight)
    finally:
      slicer.app.resumeRender()
      qt.QApplication.restoreOverrideCursor()

class CurveComparisonLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):

  WEIGHTS_COLUMN_NAME = "Weights"
  AVERAGE_DISTANCE_COLUMN_NAME = "Average distance (mm)"
  MAX_DISTANCE_COLUMN_NAME = "Max distance (mm)"
  OVERLAP_PERCENT_COLUMN_NAME = "Overlap percent (%)"
  ISO_OVERLAP_COLUMN_NAME = "ISO overlap"

  ISO_REGIONS_ARRAY_NAME = "ISO-Regions"

  NUMBER_OF_ISO_REGIONS = 6

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    VTKObservationMixin.__init__(self)

  def runCurveOptimization(self, inputCurveNode, outputTableNode):
    """
    :param inputCurveNode: User placed curve node to be optimized
    """
    inputCurvePolyData = vtk.vtkPolyData()
    inputCurvePolyData.SetPoints(inputCurveNode.GetCurvePointsWorld())

    inputPointLocator = vtk.vtkPointLocator()
    inputPointLocator.SetDataSet(inputCurvePolyData)
    inputPointLocator.BuildLocator()

    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetInputData(inputCurveNode.GetShortestDistanceSurfaceNode().GetPolyData())
    modelToWorldTransform = vtk.vtkGeneralTransform()
    slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(inputCurveNode.GetShortestDistanceSurfaceNode().GetParentTransformNode(), None, modelToWorldTransform)
    transformFilter.SetTransform(modelToWorldTransform)
    transformFilter.Update()

    inputPolyDataLocator = vtk.vtkPointLocator()
    inputPolyDataLocator.SetDataSet(transformFilter.GetOutput())
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

    optimizerCurve = slicer.mrmlScene.GetFirstNodeByName("CurveComparisonPreview")
    if optimizerCurve is None:
      optimizerCurve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFreeSurferCurveNode", "CurveComparisonPreview")
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

  def setCurveNodeWeights(self, freeSurferCurveNode, weights):
    freeSurferCurveNode.SetDistanceWeight(weights[0])
    freeSurferCurveNode.SetCurvatureWeight(weights[1])
    freeSurferCurveNode.SetSulcalHeightWeight(weights[2])
    freeSurferCurveNode.SetDistanceCurvatureWeight(weights[3])
    freeSurferCurveNode.SetDistanceSulcalHeightWeight(weights[4])
    freeSurferCurveNode.SetCurvatureSulcalHeightWeight(weights[5])
    freeSurferCurveNode.SetDistanceCurvatureSulcalHeightWeight(weights[6])
    freeSurferCurveNode.SetDirectionWeight(weights[7])

  def getLowestAverageDistanceWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    averageDistanceArray = tableNode.GetTable().GetColumnByName(self.AVERAGE_DISTANCE_COLUMN_NAME)

    lowestAverageDistanceIndex = -1
    lowestAverageDistance = vtk.VTK_DOUBLE_MAX
    for i in range(weightsArray.GetNumberOfValues()):
      average = averageDistanceArray.GetValue(i)
      if average <= lowestAverageDistance:
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
      if maxDistance <= lowestMaxDistance:
        lowestMaxDistance = maxDistance
        lowestMaxDistanceIndex = i
    weight = weightsArray.GetValue(lowestMaxDistanceIndex)
    return weight, lowestMaxDistanceIndex

  def getHighestOverlapPercentWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    overlapPercentArray = tableNode.GetTable().GetColumnByName(self.OVERLAP_PERCENT_COLUMN_NAME)

    highestOverlapPercentIndex = -1
    highestOverlapPercent = vtk.VTK_DOUBLE_MIN
    for i in range(weightsArray.GetNumberOfValues()):
      overlapPercent = overlapPercentArray.GetValue(i)
      if overlapPercent >= highestOverlapPercent:
        highestOverlapPercent = overlapPercent
        highestOverlapPercentIndex = i
    weight = weightsArray.GetValue(highestOverlapPercentIndex)
    return weight, highestOverlapPercent

  def getHighestISOOverlapWeight(self, tableNode):
    weightsArray = tableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    isoOverlapArray = tableNode.GetTable().GetColumnByName(self.ISO_OVERLAP_COLUMN_NAME)

    highestISOOverlapIndex = -1
    highestISOOverlap = vtk.VTK_DOUBLE_MIN
    for i in range(weightsArray.GetNumberOfValues()):
      isoOverlap = isoOverlapArray.GetValue(i)
      if isoOverlap >= highestISOOverlap:
        highestISOOverlap = isoOverlap
        highestISOOverlapIndex = i
    weight = weightsArray.GetValue(highestISOOverlapIndex)
    return weight, highestISOOverlap

  def evaluateWeights(self, inputCurveNode, optimizerCurveNode, weights, inputCurveLocator, inputPolyDataLocator, outputTableNode):
    # [d,   c,   h,  dc,  dh,  ch, dch,   p]
    self.setCurveNodeWeights(optimizerCurveNode, weights)

    polyData = inputCurveNode.GetShortestDistanceSurfaceNode().GetPolyData()

    pointData = polyData.GetPointData()
    isoRegionsArray = pointData.GetArray(self.ISO_REGIONS_ARRAY_NAME)

    isoRegionSum = np.zeros(self.NUMBER_OF_ISO_REGIONS + 1)

    optimizerPoints_World = optimizerCurveNode.GetCurvePointsWorld()
    averageDistance2 = 0.0
    maxDistance2 = 0.0
    overlapPercent = 0.0
    for i in range(optimizerPoints_World.GetNumberOfPoints()):
      optimizerPoint_World = optimizerPoints_World.GetPoint(i)
      closestInputPointID = inputCurveLocator.FindClosestPoint(optimizerPoint_World)
      closestPoint_World = inputCurveNode.GetCurvePointsWorld().GetPoint(closestInputPointID)
      distance2 = vtk.vtkMath.Distance2BetweenPoints(optimizerPoint_World, closestPoint_World)
      averageDistance2 += (distance2/optimizerPoints_World.GetNumberOfPoints())
      if distance2 > maxDistance2:
        maxDistance2 = distance2
      if distance2 == 0.0:
        overlapPercent += 1.0 / optimizerPoints_World.GetNumberOfPoints()

      polyDataPointID = inputPolyDataLocator.FindClosestPoint(optimizerPoint_World)
      isoRegion = isoRegionsArray.GetValue(polyDataPointID)
      if isoRegion < 0 or isoRegion > self.NUMBER_OF_ISO_REGIONS:
        continue
      isoRegionSum[isoRegion] += 1

    import math

    weightsArray = outputTableNode.GetTable().GetColumnByName(self.WEIGHTS_COLUMN_NAME)
    weightsArray.InsertNextValue(str(weights))

    averageDistance = math.sqrt(averageDistance2)
    averageDistanceArray = outputTableNode.GetTable().GetColumnByName(self.AVERAGE_DISTANCE_COLUMN_NAME)
    averageDistanceArray.InsertNextTuple1(averageDistance)

    maxDistance = math.sqrt(maxDistance2)
    maxDistanceArray = outputTableNode.GetTable().GetColumnByName(self.MAX_DISTANCE_COLUMN_NAME)
    maxDistanceArray.InsertNextTuple1(math.sqrt(maxDistance))

    overlapPercentArray = outputTableNode.GetTable().GetColumnByName(self.OVERLAP_PERCENT_COLUMN_NAME)
    overlapPercentArray.InsertNextTuple1(overlapPercent)

    isoOverlap = 0.0
    penalty = 1.0 / self.NUMBER_OF_ISO_REGIONS
    for isoRegion in range(1, self.NUMBER_OF_ISO_REGIONS+1):
      regionSum = isoRegionSum[isoRegion]
      fr = regionSum / optimizerPoints_World.GetNumberOfPoints()
      subtotal = (1 - (fr * (1 + (penalty * (isoRegion - 1)))))
      isoOverlap += subtotal
    isoOverlap /= self.NUMBER_OF_ISO_REGIONS

    isoOverlapArray = outputTableNode.GetTable().GetColumnByName(self.ISO_OVERLAP_COLUMN_NAME)
    isoOverlapArray.InsertNextTuple1(isoOverlap)

    logging.info("{0}: Average distance: {1}, Max distance: {2}, Overlap percent: {3}, ISO Overlap: {4} ||| {5}".format(
      str(weights), str(averageDistance), str(maxDistance), str(overlapPercent), str(isoOverlap), str(isoRegionSum)))

  def createISORegionOverlay(self, curveNode):
    """
    :param curve: The curve that the overlay will be created from (vtkMRMLMarkupsCurveNode)
    """
    modelNode = curveNode.GetShortestDistanceSurfaceNode()
    polyData = modelNode.GetPolyData()
    if polyData is None:
      # No polydata. Nothing to compute overlay on.
      return

    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetInputData(polyData)
    modelToWorldTransform = vtk.vtkGeneralTransform()
    slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(modelNode.GetParentTransformNode(), None, modelToWorldTransform)
    transformFilter.SetTransform(modelToWorldTransform)
    transformFilter.Update()
    polyData = transformFilter.GetOutput()

    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(transformFilter.GetOutput())
    pointLocator.BuildLocator()

    curvePoints = curveNode.GetCurvePointsWorld()

    pointData = polyData.GetPointData()
    isoRegionsArray = pointData.GetArray(self.ISO_REGIONS_ARRAY_NAME)
    if isoRegionsArray is None:
      isoRegionsArray = vtk.vtkIdTypeArray()
      isoRegionsArray.SetName(self.ISO_REGIONS_ARRAY_NAME)
    isoRegionsArray.SetNumberOfValues(polyData.GetNumberOfPoints())
    isoRegionsArray.Fill(-1)
    modelNode.AddPointScalars(isoRegionsArray)

    visitedPoints = []
    previousISORegion = []
    for regionIndex in range(self.NUMBER_OF_ISO_REGIONS+1):
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

    if modelNode.GetDisplayNode():
      modelNode.GetDisplayNode().Modified()

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
    return (np.array(list(np.binary_repr(num).zfill(m))).astype(np.int8)).tolist()
