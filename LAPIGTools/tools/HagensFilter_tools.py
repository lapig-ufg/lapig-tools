#-------------------------------------------------------------------------------
# Name:        SthephenFilter to processing TimeSeries Images
# Purpose:
#
# Author:      bernard.oliveira apud:Sthephen Hangen
#
# Created:     25/09/2015
# Copyright:   (c) bernard.oliveira 2015
# Licence:     GNL
#-------------------------------------------------------------------------------


from osgeo import gdal
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *
import numpy as np
import glob, os, math

#Create Typical Year - Finalizado 29.01.2016
def AveregeYearDoy(aEVI2,aFlag,nComposites,GoodFlags,XSIZE):
	
	iMult = []
	iFlag = []	
	for i in range(nComposites):				
		iAverengemedian = np.zeros((1,XSIZE),dtype=np.float32)
		iFlagmedian = np.zeros((1,XSIZE),dtype=np.byte)
		
		for j in range(i,len(aEVI2),nComposites):
			iGoodFLAGS = np.where(aFlag[j]==GoodFlags,1.0,0.0)
			iFill = aEVI2[j]*iGoodFLAGS					
			iAverengemedian += iFill
			iFlagmedian += iGoodFLAGS
		
		iNan = np.where(iFlagmedian==0.0,1,iFlagmedian)
		iMean = iAverengemedian/iNan						
		
		iMult.append(iMean)
		iFlag.append(iFlagmedian)
	
	return [iMult,iFlag]
		

#Desvio de cada dia na serie temporal em relacao a media do ano - Finalizado 29.01.2016
def DevAveregeAnual(iArray,iFlag,nComposites,aAveregeYearDoy,GoodFlags,XSIZE):
	
		aAveregeTA = np.zeros((1,XSIZE),dtype=np.float32)
		fAveregeTA = np.zeros((1,XSIZE),dtype=np.byte)
		for i in range(nComposites):
			for j in range(i,len(iArray),nComposites):
				 iGoodFLAGS = np.where(iFlag[j]==GoodFlags,1.0,0.0)
				 iFill = iArray[j]*iGoodFLAGS
				 AveregeFill = aAveregeYearDoy[i]*iGoodFLAGS
				 dTA = (AveregeFill-iFill)*(AveregeFill-iFill)
				 aAveregeTA +=dTA
				 fAveregeTA +=iGoodFLAGS
		aAveregeTypicalAnual = np.sqrt(aAveregeTA/fAveregeTA)
		return aAveregeTypicalAnual

#Desvio entre a vizinhanco do dia anterior e posterior - Finalizado 29.01.2016
def DevNeighborhoodDay(iArray,iFlag,GoodFlags,XSIZE):
		
		aAveregeND = np.zeros((1,XSIZE),dtype=np.float32)
		aAveregeFlag = np.zeros((1,XSIZE),dtype=np.byte)
		for i in range(len(iArray)):
			if ((i > 0) and (i < len(iArray)-1)):
				fBefore = iFlag[i-1]
				fAfter = iFlag[i+1]
				fAtual = iFlag[i]
				iBefore = iArray[i-1]
				iAfter = iArray[i+1]
				iAtual = iArray[i]
				m = np.where((fBefore==GoodFlags) & (fAfter==GoodFlags) & (fAtual==GoodFlags))
				if np.size(m) > 0:
					tDay = (iBefore[m]+iAfter[m])/2
					vDay = (tDay - iAtual[m])*(tDay - iAtual[m])
					aAveregeND[m] += vDay
					aAveregeFlag[m] += 1
		aAveregeTypicalDay = np.sqrt(aAveregeND/aAveregeFlag)
		return aAveregeTypicalDay

#Desvio entre a vizinhanco do dia anterior e posterior - Finalizado 29.01.2016
def DevNeighborhoodAnual(iArray,iFlag,nComposites,GoodFlags,XSIZE): 
		yAveregeND = np.zeros((1,XSIZE),dtype=np.float32) 
		yAveregeFlag = np.zeros((1,XSIZE),dtype=np.byte) 
		aAveregeTypicalDay = np.zeros((1,XSIZE),dtype=np.float32)
		for i in range(nComposites): 
			for j in range(i,len(iArray),nComposites): 
				if (j >= nComposites) and (j <= (len(iArray)-1)-nComposites):
					fBefore = iFlag[j-nComposites] 
					fAfter = iFlag[j+nComposites] 
					fAtual = iFlag[j] 
					iBefore = iArray[j-nComposites] 
					iAfter = iArray[j+nComposites] 
					iAtual = iArray[j]	
					m = np.where((fBefore==GoodFlags) & (fAfter==GoodFlags) & (fAtual==GoodFlags)) 
					if np.size(m) > 0: 
						tYear = (iBefore[m]+iAfter[m])/2 
						vYear = (tYear - iAtual[m])*(tYear - iAtual[m]) 
						yAveregeND[m] += vYear 
						yAveregeFlag[m] += 1 
		if len(yAveregeND) > 0:
			 aAveregeTypicalDay = np.sqrt(yAveregeND/yAveregeFlag)
		else:
			 aAveregeTypicalDay = None
		return aAveregeTypicalDay

#Preenchimento dos buracos (FillGaps) - Em desenvolvimento 29.01.2006
def FillGaps(iArray,iFlag,nComposites,iAveregeDOY,iAveregeAnual,iNeighborhoodDay,iNeighborhoodAnual,GoodFlags,XSIZE):
		
	ListGaps = []
	for i in range(len(iArray)):
		
		#iGaps = np.zeros((1,XSIZE),dtype=np.float32) 			
		iGaps = iArray[i]
		locationFlags = np.where(iFlag[i]>GoodFlags)
		iGaps[locationFlags] = 0.0
				
		numerador = 0.0 
		denominador = 0.0  					
		
		lAnual = np.where(iNeighborhoodAnual == 0,1,iNeighborhoodAnual)			
		lDay = np.where(iNeighborhoodDay == 0,1,iNeighborhoodDay)
		numerador += iAveregeDOY[i%nComposites]*(float(1)/iAveregeAnual) 
		denominador += (float(1)/iAveregeAnual)  
				
		#Verificar se a vizinhanca local os valores sao bons
		if (i != 0 and i != len(iArray)-1):
				fBefore = iFlag[i-1] 
				fAfter = iFlag[i+1] 
				fAtual = iFlag[i]
				iBefore = iArray[i-1] 
				iAfter = iArray[i+1] 
				iAtual = iArray[i]
				m = np.where((fBefore == GoodFlags) & (fAfter == GoodFlags) & (fAtual == GoodFlags)) 
				if np.size(m) > 0:
					fBefore = fBefore*0
					fBefore[m] = 1
					fAfter = fAtual*0
					fAfter[m] = 1
					iBefore = iBefore*fBefore
					iAfter = iAfter*fAfter 
					numerador += ((iBefore+iAfter)/float(2))*(float(1)/lDay) 
					denominador += float(1)/lDay		  					
						
		#Verificar se a vizinhanca anual os valores sao bons
		if (i >= nComposites) and (i <= (len(iArray)-1)-nComposites): 
				faBefore = iFlag[i-nComposites]
				faAfter = iFlag[i+nComposites]
				faAtual = iFlag[i]
				iaBefore = iArray[i-nComposites]
				iaAfter = iArray[i+nComposites]
				iaAtual = iArray[i]
				n = np.where((faBefore==GoodFlags) & (faAfter==GoodFlags) & (faAtual==GoodFlags))
				if np.size(n):
					faBefore = faBefore*0
					faBefore[m]=1
					faAfter = faAfter*0
					fAfter[m] = 1
					iaBefore = iBefore*fBefore
					iaAfter = iAfter*fAfter 
					numerador += ((iaBefore+fAfter)/float(2))*(float(1)/lAnual)
					denominador += float(1)/lAnual  
				
		fGap = numerador/denominador
		iGaps[locationFlags] = fGap[locationFlags]
		ListGaps.append(iGaps)
		iGaps = None
	return ListGaps
