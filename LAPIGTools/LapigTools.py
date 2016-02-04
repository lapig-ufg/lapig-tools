#import modules menu plugin
#---------------

import inspect
import tools
import resources
from .tools.GenericTool import GenericTool
import qgis.utils
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QMessageBox,QMenu

class LapigTools:
	
	def __init__(self, iface):
		self.iface = iface
		
		self.menu = QMenu( "&LAPIG Tools", self.iface.mainWindow().menuBar() )
		self.submenu = QMenu("&Time Series Filters")
		self.menu.addMenu(self.submenu)
		
		self.tools = []
		for key, clazz in tools.__dict__.iteritems():
			if inspect.isclass(clazz) and issubclass(clazz, GenericTool) and key != 'GenericTool':
				self.tools.append(clazz(iface))

	def initGui(self):
		List = []
		ListLabel = []
		for tool in self.tools:
			listA,label = tool.initGui()
			List.append(listA)
			ListLabel.append(label)
				
		for i in range(len(List)):
			
			if (ListLabel[i] == 'Savitzky Golay Filter') or (ListLabel[i] == 'Hagens Filter'):
				self.submenu.addAction(List[i])
				self.iface.mainWindow().menuBar().insertMenu(List[i],self.menu)
			else:	
				self.menu.addAction(List[i])
				self.iface.mainWindow().menuBar().insertMenu(List[i], self.menu)
				
		
	def unload(self):
		for tool in self.tools:
			tool.unload()
		self.menu.deleteLater()	