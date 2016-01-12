#import modules menu plugin
#---------------

import inspect
import tools
import resources
from .tools.GenericTool import GenericTool
import qgis.utils

class LapigTools:
	
	def __init__(self, iface):
		self.iface = iface

		self.tools = []
		for key, clazz in tools.__dict__.iteritems():
			if inspect.isclass(clazz) and issubclass(clazz, GenericTool) and key != 'GenericTool':
				self.tools.append(clazz(iface))

	def initGui(self):
		for tool in self.tools:
			tool.initGui()
	
	def unload(self):
		for tool in self.tools:
			tool.unload()