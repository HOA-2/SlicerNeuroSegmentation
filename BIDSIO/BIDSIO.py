import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin

#
# BIDSIO
#
class BIDSIO(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # Setting attributes
  CURRENT_DIRECTORY_SETTING = "NeuroSeg/CurrentDirectory"
  SUBJECT_NAME_PARAMETER = "SubjectName"
  SESSION_NAME_PARAMETER = "SessionName"

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "BIDSIO"
    self.parent.categories = ["Utilities"]
    self.parent.dependencies = ["Data"]
    self.parent.contributors = ["Kyle Sunderland (Perk Lab, Queen's University)"]
    self.parent.helpText = """
This is a module that organizes a workflow for brain segmentation.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Kyle Sunderland (Perk Lab, Queen's University), and was partially funded by Brigham and Women’s Hospital through NIH grant R01MH112748
"""
    if not slicer.app.commandOptions().noMainWindow:
      slicer.app.connect("startupCompleted()", self.initializeModule)

  def initializeModule(self):
    moduleWidget = slicer.modules.bidsio.widgetRepresentation().self()

    #qt.QTimer.singleShot(1, moduleWidget.showLoadSessionDialog) # Disabled for now

    loadSessionIcon = qt.QIcon(moduleWidget.resourcePath('Icons/LoadSession.png'))
    self.loadSessionAction = slicer.util.mainWindow().findChild("QToolBar").addAction("")
    self.loadSessionAction.setIcon(loadSessionIcon)
    self.loadSessionAction.triggered.connect(moduleWidget.showLoadSessionDialog)

    saveSessionIcon = qt.QIcon(moduleWidget.resourcePath('Icons/SaveSession.png'))
    self.saveSessionAction = slicer.util.mainWindow().findChild("QToolBar").addAction("")
    self.saveSessionAction.setIcon(saveSessionIcon)
    self.saveSessionAction.triggered.connect(moduleWidget.showSaveSessionDialog)

class LoadSessionDialog(qt.QDialog):
  def __init__(self, parent):
    qt.QDialog.__init__(self, parent)
    self.setWindowTitle("Load session")

    layout = qt.QVBoxLayout()
    self.setLayout(layout)

    moduleWidget = slicer.modules.bidsio.widgetRepresentation().self()
    uiWidget = slicer.util.loadUI(moduleWidget.resourcePath('UI/LoadSessionWidget.ui'))
    layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)   
    self.ui.directoryButton.directory = moduleWidget.getCurrentDirectory()

    # Connections
    self.ui.directoryButton.directoryChanged.connect(self.onDirectoryChanged)
    self.ui.loadButton.clicked.connect(self.loadSelectedSession)
    self.ui.treeWidget.itemSelectionChanged.connect(self.onTreeSelectionChanged)

    self.onDirectoryChanged()

  def onDirectoryChanged(self):
    currentDirectory = self.ui.directoryButton.directory
    directory = qt.QDir(currentDirectory)

    self.ui.treeWidget.clear()
    subjectInfoList = directory.entryInfoList(qt.QDir.Dirs | qt.QDir.NoDotAndDotDot)

    moduleWidget = slicer.modules.bidsio.widgetRepresentation().self()
    moduleWidget.setCurrentDirectory(currentDirectory)

    for subjectInfo in subjectInfoList:
      subjectName = subjectInfo.fileName()
      subjectItem = qt.QTreeWidgetItem();
      subjectItem.setData(0, qt.Qt.UserRole, subjectName)
      subjectItem.setData(0, qt.Qt.UserRole, subjectName)
      subjectItem.setText(0, subjectName)
      subjectItem.setText(2, subjectInfo.lastModified().toString())
      self.ui.treeWidget.addTopLevelItem(subjectItem)

      subjectPath = self.ui.directoryButton.directory + "/" + subjectInfo.fileName()
      subjectDir = qt.QDir(subjectPath)
      sessionInfoList = subjectDir.entryInfoList(qt.QDir.Dirs | qt.QDir.NoDotAndDotDot)
      for sessionInfo in sessionInfoList:
        sessionName = sessionInfo.fileName()
        scenePath = subjectPath + "/" + sessionName + "/scene.mrml"
        if not os.access(scenePath, os.F_OK):
          continue

        sessionItem = qt.QTreeWidgetItem();
        sessionItem.setData(0, qt.Qt.UserRole, subjectName)
        sessionItem.setData(0, qt.Qt.UserRole + 1, sessionName)
        sessionItem.setText(1, sessionName)
        sessionItem.setText(2, sessionInfo.lastModified().toString())
        subjectItem.addChild(sessionItem)

  def onTreeSelectionChanged(self):
    selectedItems = self.ui.treeWidget.selectedItems()
    sessionName = None
    if len(selectedItems) > 0:
      selectedItem = selectedItems[0]
      sessionName = selectedItem.data(0, qt.Qt.UserRole + 1)
    self.ui.loadButton.enabled = not sessionName is None

  def loadSelectedSession(self):
    selectedItems = self.ui.treeWidget.selectedItems()
    if len(selectedItems) > 0:
      selectedItem = selectedItems[0]
      subjectName = selectedItem.data(0, qt.Qt.UserRole)
      sessionName = selectedItem.data(0, qt.Qt.UserRole + 1)

    if subjectName == "" or sessionName == "":
      return

    moduleLogic = slicer.modules.bidsio.widgetRepresentation().self().logic
    if moduleLogic.loadSession(self.ui.directoryButton.directory, subjectName, sessionName):
      self.close()
    else:
      slicer.util.errorDisplay("Error loading session!")

class SaveSessionDialog(qt.QDialog):
  def __init__(self, parent):
    qt.QDialog.__init__(self, parent)
    self.setWindowTitle("Save session")

    layout = qt.QVBoxLayout()
    self.setLayout(layout)

    moduleWidget = slicer.modules.bidsio.widgetRepresentation().self()
    uiWidget = slicer.util.loadUI(moduleWidget.resourcePath('UI/SaveSessionWidget.ui'))
    layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    settings = qt.QSettings()
    self.ui.directoryButton.directory = settings.value(BIDSIO.CURRENT_DIRECTORY_SETTING, slicer.app.defaultScenePath)

    self.moduleWidget = slicer.modules.bidsio.widgetRepresentation().self()
    self.logic = self.moduleWidget.logic
    parameterNode = self.logic.getParameterNode()
    subjectName = self.logic.getSubjectName()
    sessionName = self.logic.getSessionName()
    self.ui.subjectNameEdit.text = subjectName
    self.ui.sessionNameEdit.text = sessionName

    # Connections
    self.ui.saveButton.clicked.connect(self.save)
    self.ui.subjectNameEdit.textChanged.connect(self.onSubjectSessionNameChanged)
    self.ui.sessionNameEdit.textChanged.connect(self.onSubjectSessionNameChanged)
    self.onSubjectSessionNameChanged()

  def onSubjectSessionNameChanged(self):
    subjectName = self.ui.subjectNameEdit.text
    sessionName = self.ui.sessionNameEdit.text
    self.ui.saveButton.enabled = subjectName != "" and sessionName != ""

  def progressCallback(progressDialog, progressLabel, progressValue):
    progressDialog.labelText = progressLabel
    slicer.app.processEvents()
    progressDialog.setValue(progressValue)
    slicer.app.processEvents()
    return progressDialog.wasCanceled

  def save(self):
    self.logic.setSubjectName(self.ui.subjectNameEdit.text)
    self.logic.setSessionName(self.ui.sessionNameEdit.text)

    subjectName = self.logic.getSubjectName()
    sessionName = self.logic.getSessionName()
    
    sessionDirectory = self.ui.directoryButton.directory + "/" + subjectName
    if sessionName != "":
      sessionDirectory += "/" + sessionName
    scenePath = sessionDirectory + "/scene.mrml"

    if os.access(scenePath, os.F_OK) and not slicer.util.confirmOkCancelDisplay("Session already exists! Do you want to overwrite?"):
      return

    progressDialog = slicer.util.createProgressDialog(parent=self, value=0, maximum=100)
    progressCallbackFunction = lambda progressLabel, progressValue, progressDialog=progressDialog: SaveSessionDialog.progressCallback(progressDialog, progressLabel, progressValue)

    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    success = self.logic.saveSession(self.ui.directoryButton.directory, progressCallbackFunction)
    qt.QApplication.restoreOverrideCursor()

    if success:
      self.close()
      slicer.util.infoDisplay("Saving successful!")
    else:
      slicer.util.errorDisplay("Error saving session!")

#
# BIDSIOWidget
#

class BIDSIOWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

  def showLoadSessionDialog(self):
    loadSessionDialog = LoadSessionDialog(slicer.util.mainWindow())
    loadSessionDialog.deleteLater()
    loadSessionDialog.exec_()

  def showSaveSessionDialog(self):
     saveSessionDialog = SaveSessionDialog(slicer.util.mainWindow())
     saveSessionDialog.deleteLater()
     saveSessionDialog.exec_()

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = BIDSIOLogic()

    uiWidget = slicer.util.loadUI(self.resourcePath('UI/BIDSIO.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    uiWidget.setMRMLScene(slicer.mrmlScene)

  def getPath(self):
    return os.path.dirname(slicer.modules.bidsio.path)

  def getCurrentDirectory(self):
    settings = qt.QSettings()
    return settings.value(BIDSIO.CURRENT_DIRECTORY_SETTING, slicer.mrmlScene.GetRootDirectory())

  def setCurrentDirectory(self, directory):
    settings = qt.QSettings()
    settings.setValue(BIDSIO.CURRENT_DIRECTORY_SETTING, directory)

  def cleanup(self):
    self.removeObservers()

#
# BIDSIOLogic
#

class BIDSIOLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def loadSession(self, subjectDirectory, subjectName, sessionName):
    sessionDirectoryPath = subjectDirectory + "/" + subjectName + "/" + sessionName
    sessionDirectory = qt.QDir(sessionDirectoryPath)
    sessionDirectory.setNameFilters(["*.mrml"])

    mrmlFilesList = sessionDirectory.entryList()
    loaded = False
    if len(mrmlFilesList) > 0:
      properties = {}
      properties["clear"] = True
      try:
        slicer.util.loadScene(os.path.join(sessionDirectoryPath, mrmlFilesList[0]))
      except:
        return False

    self.setSessionName(sessionName)
    self.setSubjectName(subjectName)
    return True

  def setSessionName(self, sessionName):
    parameterNode = self.getParameterNode()
    if parameterNode:
      parameterNode.SetParameter(BIDSIO.SESSION_NAME_PARAMETER, sessionName)

  def getSessionName(self):
    parameterNode = self.getParameterNode()
    if parameterNode:
      sessionName = parameterNode.GetParameter(BIDSIO.SESSION_NAME_PARAMETER)
      if sessionName is not None:
        return sessionName
    return ""

  def setSubjectName(self, subjectName):
    parameterNode = self.getParameterNode()
    if parameterNode:
      parameterNode.SetParameter(BIDSIO.SUBJECT_NAME_PARAMETER, subjectName)

  def getSubjectName(self):
    parameterNode = self.getParameterNode()
    if parameterNode:
      subjectName = parameterNode.GetParameter(BIDSIO.SUBJECT_NAME_PARAMETER)
      if subjectName is not None:
        return subjectName
    return ""

  def saveSession(self, subjectDirectory, progressCallback=None):
    subjectName = self.getSubjectName()
    sessionName = self.getSessionName()

    sceneSaveDirectory = subjectDirectory + "/" + subjectName
    saveMessage = "Saving scene for subject {0}".format(subjectName)
    if (not sessionName is None) and sessionName != "":
      saveMessage = ", session {0}".format(sessionName)
      sceneSaveDirectory = sceneSaveDirectory + "/" + sessionName
    logging.info(saveMessage)
    slicer.app.ioManager().addDefaultStorageNodes()

    fileNames = []

    progress = 0.0
    nodesSaved = 0
    nodes = slicer.mrmlScene.GetNodes()
    nodesToSaveCount = 0
    for node in nodes:
      if node and node.IsA("vtkMRMLStorableNode") and node.GetSaveWithScene():
        nodesToSaveCount += 1

    for node in nodes:
      if node is None:
        continue
      if not node.IsA("vtkMRMLStorableNode"):
        continue
      if not node.GetSaveWithScene():
        continue
      if node.GetStorageNode() is None:
        continue

      if progressCallback is not None and progressCallback('\nSaving node: %s' % node.GetName(), progress):
        break

      storageNode = node.GetStorageNode()
      fileExtension = "." + storageNode.GetDefaultWriteFileExtension()
      if node.IsA("vtkMRMLVolumeNode") or node.IsA("vtkMRMLSegmentationNode"):
        nodeDirectory = os.path.join(sceneSaveDirectory, "anat")
      else:
        nodeDirectory = os.path.join(sceneSaveDirectory, "data")
      if not os.access(nodeDirectory, os.F_OK):
        os.makedirs(nodeDirectory)
      if node.IsA("vtkMRMLVolumeNode"):
        fileExtension = ".nii.gz" # BIDS specification requires that images are saved in NIFTI
      elif node.IsA("vtkMRMLSegmentationNode"):
        pass # Segmentation nodes can only be saved as .seg.nrrd. BIDS would prefer .nii.gz

      # Save node
      fileName = slicer.app.applicationLogic().PercentEncode(node.GetName())
      if node.IsA("vtkMRMLSegmentationNode"):
         masterVolumeNode = node.GetNodeReference("referenceImageGeometryRef")
         masterVolumeName = slicer.app.applicationLogic().PercentEncode(masterVolumeNode.GetName())
         # Node name is derived from the name of the master volume
         fileName = masterVolumeName + "_space-LPS_dseg" # Discrete segmentation name from BIDS extension proposal 11
         # https://docs.google.com/document/d/1YG2g4UkEio4t_STIBOqYOwneLEs1emHIXbGKynx7V0Y/edit#heading=h.mqkmyp254xh6

      fileRenamed = False
      for name in fileNames:
        if fileName == name:
          fileRenamed = True
          fileName = slicer.mrmlScene.GenerateUniqueName(name)
          logging.info(
            "Filename {0} already exists for another node in the currently saving scene, {1} filename will be used instead".format(
            name + fileExtension, fileName + fileExtension))
          break

      nodeSavePath = os.path.join(nodeDirectory, fileName + fileExtension)
      fileNames.append(fileName)
      storageNode.SetFileName(nodeSavePath)
      nodeAlreadySavedInThisDir = os.path.isfile(nodeSavePath)
      if (not nodeAlreadySavedInThisDir) or node.GetModifiedSinceRead() or fileRenamed:
        logging.info("Saving node {0} with ID: {1}".format(node.GetName(), node.GetID()))
        if not storageNode.WriteData(node):
          logging.error("Saving node ID {0} failed".format(node.GetID()))
          logging.error("Saving failed")
          return False
        logging.info("Node with ID {0} successfully saved".format(node.GetID()))

      nodesSaved += 1
      progress = (100.0 * nodesSaved) / (nodesToSaveCount+1)

    if progressCallback is not None and progressCallback('\nSaving scene', progress):
      return False

    # Save scene file
    if not os.access(sceneSaveDirectory, os.F_OK):
      os.makedirs(sceneSaveDirectory)

    sceneName = "scene.mrml"
    if slicer.mrmlScene.GetModifiedSinceRead():
      file_path = os.path.join(sceneSaveDirectory, sceneName)
      if not slicer.mrmlScene.Commit(file_path):
        logging.error("Scene saving failed")
        return False

    if progressCallback is not None and progressCallback('\nSaving complete', 100.0):
      return False
    return True

class BIDSIOTest(ScriptedLoadableModuleTest):
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
    self.test_BIDSIO1()

  def test_BIDSIO1(self):
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
