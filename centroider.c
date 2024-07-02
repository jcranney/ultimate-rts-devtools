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

// TODO: check YON/OGU when to define this (compile vs runtime?)
const uint32_t N_SLOPE = 512;

int main()
{
	// ----------- Define WFS image
	IMAGE *wfs_image;      // pointer to image
	int NB_WFS_IMAGES = 1; // can hold 1 image
	
	// allocate memory for array of images
	wfs_image = (IMAGE*) malloc(sizeof(IMAGE)*NB_WFS_IMAGES);
	

	// ----------- Define slope vector
	IMAGE *slope_vec;      // pointer to slopes
	int NB_SLOPE_VECS = 1; // can hold 1 image
	long n_axis;           // number of axis
	uint8_t atype;         // data type
	uint32_t *arr_size;    // vector dimensions 
	int shared;            // 1 if image in shared memory
	int NBkw;              // number of keywords supported
	int CBSize;            // number of keywords supported
	
	// allocate memory for array of images
	slope_vec = (IMAGE*) malloc(sizeof(IMAGE)*NB_WFS_IMAGES);
	
	// slope vector image will be 1D
	n_axis = 1;
	
	// vector size will be (NSLOPE,)
	arr_size = (uint32_t *) malloc(sizeof(uint32_t)*n_axis);
	arr_size[0] = N_SLOPE;
	
	// vector will be float type
	// see file ImageStruct.h for list of supported types
	atype = _DATATYPE_FLOAT;
	
	// vector will be in shared memory
	shared = 1;
	
	// allocate space for 10 keywords
	NBkw = 10; // TODO: check YON/OGU

    // no circular buffer
    CBSize = 1; // TODO: check YON/OGU

    // read wfs image from shared memory
    // TODO: index this as an argument to the executable,
	//       or build 5 different executables
    ImageStreamIO_openIm(wfs_image,"lgswfs00");

	// create slope vector in shared memory
	ImageStreamIO_createIm(
		&slope_vec[0], "slopes00", n_axis, 
		arr_size, atype, shared, NBkw, CBSize
	);

	int s;
	int semval;

	// writes a square in image
	// square location rotates around center
	while (1)
	{
		ImageStreamIO_semwait(wfs_image, 0); // TODO: check with YON/OGU
											 // This seems to run a few times
											 // before catching that the semaphore
											 // is up to date? (if that's how it
											 // works)

		// get middle row and write to vec
		slope_vec[0].md[0].write = 1; // set this flag to 1 when writing data
		
		for(int ii=0; ii<wfs_image[0].md[0].size[0]; ii++) {
			for(int jj=0; jj<wfs_image[0].md[0].size[1]; jj++)
			{
				if (jj != 256) continue;
				
				slope_vec[0].array.F[ii] = wfs_image[0].array.F[jj*wfs_image[0].md[0].size[0]/2+ii];
			}
		}
		
		// POST ALL SEMAPHORES
		ImageStreamIO_sempost(&wfs_image[0], -1);
		
		slope_vec[0].md[0].write = 0; // Done writing data
		slope_vec[0].md[0].cnt0++;
		slope_vec[0].md[0].cnt1++;
	}
	


	free(arr_size);
	free(wfs_image);
	free(slope_vec);
	
	return 0;
}