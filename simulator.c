/*
 * Example code to write image in shared memory
 * 
 * compile with:
 * gcc ImCreate_test.c ImageStreamIO.c -lm -lpthread 
 * 
 * Required files in compilation directory :
 * ImCreate_test.c   : source code (this file)
 * ImageStreamIO.c   : ImageStreamIO source code
 * ImageStreamIO.h   : ImageCreate function prototypes
 * ImageStruct.h     : Image structure definition
 * 
 * EXECUTION:
 * ./a.out  
 * (no argument)
 * 
 * Creates an image imtest00 in shared memory
 * Updates the image every ~ 10ms, forever...
 * A square is rotating around the center of the image
 * 
 */




#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "ImageStruct.h"
#include "ImageStreamIO.h"




int main()
{
	IMAGE imarray;    // pointer to array of images
	int NBIMAGES = 1;  // can hold 1 image
	long naxis;        // number of axis
	uint8_t atype;     // data type
	uint32_t *imsize;  // image size 
	int shared;        // 1 if image in shared memory
	int NBkw;          // number of keywords supported
	int CBSize;          // number of keywords supported
	
	// image will be 2D
	naxis = 2;
	
	// image size will be 512 x 512
	imsize = (uint32_t *) malloc(sizeof(uint32_t)*naxis);
	imsize[0] = 512;
	imsize[1] = 512;
	
	// image will be float type
	// see file ImageStruct.h for list of supported types
	atype = _DATATYPE_FLOAT;
	
	// image will be in shared memory
	shared = 1;
	
	// allocate space for 10 keywords
	NBkw = 10;

    // no circular buffer
    CBSize = 1;


	
	// create an image in shared memory
	ImageStreamIO_createIm(&imarray, "lgswfs00", naxis, imsize, atype, shared, NBkw, CBSize);
    // imarray = stream_connect_create_2Df32("lgswfs00",512,512);

	float angle; 
	float r;
	float r1;
	long ii, jj;
	float x, y, x0, y0, xc, yc;
	// float squarerad=20;
	long dtus = 1000; // update every 1ms
	float dangle = 0.02;
	
	// writes a square in image
	// square location rotates around center
	angle = 0.0;
	r = 100.0;
	x0 = 0.5*imarray.md[0].size[0];
	y0 = 0.5*imarray.md[0].size[1];
	while (1)
	{
        
		// disk location
		xc = x0 + r*cos(angle);
		yc = y0 + r*sin(angle);
		
		for(ii=0; ii<imarray.md[0].size[0]; ii++)
			for(jj=0; jj<imarray.md[0].size[1]; jj++)
			{
				x = 1.0*ii;
				y = 1.0*jj;
				float dx = x-xc;
				float dy = y-yc;
				
				imarray.array.F[jj*imarray.md[0].size[0]+ii] = cos(0.03*dx)*cos(0.03*dy)*exp(-1.0e-4*(dx*dx+dy*dy));
			}
		
		// POST ALL SEMAPHORES
        ImageStreamIO_UpdateIm(&imarray);
		
		usleep(dtus);
		angle += dangle;
		if(angle > 2.0*3.141592)
			angle -= 2.0*3.141592;
	}
	


	free(imsize);
	
	return 0;
}