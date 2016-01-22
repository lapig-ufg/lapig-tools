from osgeo import ogr, gdal
import os

def verifyImageDimension(listImages):
		
		LogError = open(os.path.join(os.path.dirname(listImages[0]),"LogErros.txt"),"w")
		Error = 0
		StandardImage = gdal.Open(listImages[0],gdal.GA_ReadOnly)			
		YSize = StandardImage.RasterYSize
		XSize = StandardImage.RasterXSize
		dtype = StandardImage.GetRasterBand(1).DataType			
		pixelx,pixely = StandardImage.GetGeoTransform()[1],StandardImage.GetGeoTransform()[5]
		for i in listImages:				
			GetImages = gdal.Open(i,gdal.GA_ReadOnly)
			
			#Check Erros
			if GetImages.RasterYSize != YSize and GetImages.RasterXSize != XSize:
				LogError.writelines("Dimension error: "+str(i)+'\n')
				Error +=1
			if GetImages.GetGeoTransform()[1] != pixelx and GetImages.GetGeoTransform()[5] != pixely:
				LogError.writelines("Pixel Size error: "+str(i)+'\n')
				Error +=1
			if GetImages.GetRasterBand(1).DataType != dtype :
				LogError.writelines("Type and Dimension error:"+str(i)+'\n')
				Error +=1
						
			GetImages = None			
		
		LogError.close()
		return Error	