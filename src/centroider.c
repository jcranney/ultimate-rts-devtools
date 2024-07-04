/*
 * Basic image calibration and centroiding for SH WFS
 * 
 * compile with:
 * gcc centroider.c ImageStreamIO.c -lm -lpthread 
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
 * Waits for SHWFS image stream to be ready, then
 * calibrates it by performing flat-fielding and 
 * dar subtraction. Then it computes the centroid
 * in pixel-space, saving the:
 *  - slope map
 *  - slope vector
 *  - flux map
 * for a given WFS.
 * 
 */




#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "ImageStruct.h"
#include "ImageStreamIO.h"
#include <string.h>

// TODO: check YON/OGU when to define this (compile vs runtime?)
const uint32_t N_SUBX = 32;
const uint32_t FOV_X = 8;
const char* WFS_ID = "00";

// Parameters that should go in config (for FPS)
const float_t COG_THRESH = 0.0; // greater than -1 implies "use threshold"
// const uint32_t j0 = 0;
// const uint32_t i0 = 0;

int main()
{

	////////////// REAL TIME INPUTS /////////////
	// ----------- Define WFS image
	IMAGE *wfs_image;      // pointer to image
	{
		int NB = 1; // can hold 1 image
		// allocate memory for array of images
		wfs_image = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		char name[] = "lgswfs";
		strcat(name,WFS_ID);
		printf(name);
 	    ImageStreamIO_openIm(wfs_image,name);
	}



	//////////// CALIBRATION INPUTS /////////////
	// ----------- WFS flat
	IMAGE *wfs_flat;      // pointer to image
	{
		int NB = 1; // can hold 1 image
		// allocate memory for array of images
		wfs_flat = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		char name[] = "wfsflat";
		strcat(name,WFS_ID);
		printf(name);
 	    ImageStreamIO_openIm(wfs_flat,name);
	}
	
	// ----------- WFS background
	IMAGE *wfs_bg;      // pointer to image
	{
		int NB = 1; // can hold 1 image
		// allocate memory for array of images
		wfs_bg = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		char name[] = "wfsbg";
		strcat(name,WFS_ID);
		printf(name);
 	    ImageStreamIO_openIm(wfs_bg,name);
	}
	/*
	// ----------- WFS pixel interpolator
	IMAGE *wfs_interp;      // pointer to image
	{
		int NB = 1; // can hold 1 image
		// allocate memory for array of images
		wfs_bg = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		char name[] = "wfsinterp";
		strcat(name,WFS_ID);
		printf(name);
 	    ImageStreamIO_openIm(wfs_interp,name);
	}
	*/

	// ----------- WFS valid subaps
	IMAGE *wfs_valid;      // pointer to image
	{
		int NB = 1; // can hold 1 image
		// allocate memory for array of images
		wfs_valid = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		char name[] = "wfsvalid";
		strcat(name,WFS_ID);
		printf(name);
 	    ImageStreamIO_openIm(wfs_valid,name);
	}




	//////////////// OUTPUTS ///////////////////
	//
	// ----------- Define slope vector
	// IMPORTANT:
	// The slope vector is long enough to hold 32x32 sub-aps (32x32x2 slopes).
	// It is the responsibility of the RTS to select the first NVALID*2 slopes
	// before reconstructing. This provides a completely static centroiding
	// process, at the cost of marginally higher network usage (~25% higher).
	// Note that this also allows live-updating of the "wfsvalid" map in shm.
	//
	// There are many other ways of doing this, so if that network overhead
	// becomes a limiting factor, it would be worth restructuring this part.
	//
	IMAGE *slope_vec;      // pointer to slopes
	{
		int NB = 1;            // can hold 1 image
		long n_axis;           // number of axis
		uint8_t atype;         // data type
		uint32_t *arr_size;    // vector dimensions 
		int shared;            // 1 if image in shared memory
		int NBkw;              // number of keywords supported
		int CBSize;            // number of keywords supported
		char name[] = "slopes";
		strcat(name,WFS_ID);
		// allocate memory for array of images
		slope_vec = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		
		// slope vector image will be 1D
		n_axis = 1;
		
		// vector size will be (NSLOPE,)
		arr_size = (uint32_t *) malloc(sizeof(uint32_t)*n_axis);
		arr_size[0] = N_SUBX*N_SUBX*2;
		
		// vector will be float type
		// see file ImageStruct.h for list of supported types
		atype = _DATATYPE_FLOAT;
		
		// vector will be in shared memory
		shared = 1;
		
		// allocate space for 10 keywords
		NBkw = 10; // TODO: check YON/OGU

		// no circular buffer
		CBSize = 1; // TODO: check YON/OGU

		// create slope vector in shared memory
		// TODO: do this using the connect_stream API instead
		ImageStreamIO_createIm(
			&slope_vec[0], name, n_axis, 
			arr_size, atype, shared, NBkw, CBSize
		);
		free(arr_size);
	}
	
	// ----------- Define slope map
	IMAGE *slope_map;      // pointer to slopemap
	{
		int NB = 1; 		   // can hold 1 image
		long n_axis;           // number of axis
		uint8_t atype;         // data type
		uint32_t *arr_size;    // array dimensions 
		int shared;            // 1 if image in shared memory
		int NBkw;              // number of keywords supported
		int CBSize;            // number of keywords supported
		char name[] = "slopemap";
		strcat(name,WFS_ID);
		// allocate memory for array of images
		slope_map = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		
		//  vector image will be 1D
		n_axis = 2;
		
		// array size will be (NSUBX,NSUBX)
		arr_size = (uint32_t *) malloc(sizeof(uint32_t)*n_axis);
		arr_size[0] = N_SUBX;
		arr_size[1] = N_SUBX*2;
		
		// vector will be float type
		// see file ImageStruct.h for list of supported types
		atype = _DATATYPE_FLOAT;
		
		// vector will be in shared memory
		shared = 1;
		
		// allocate space for 10 keywords
		NBkw = 10; // TODO: check YON/OGU

		// no circular buffer
		CBSize = 1; // TODO: check YON/OGU

		// create slope vector in shared memory
		// TODO: do this using the connect_stream API instead
		ImageStreamIO_createIm(
			&slope_map[0], name, n_axis, 
			arr_size, atype, shared, NBkw, CBSize
		);
		free(arr_size);
	}

	// ----------- Define flux map
	IMAGE *flux_map;      // pointer to flux
	{
		int NB = 1; 		   // can hold 1 image
		long n_axis;           // number of axis
		uint8_t atype;         // data type
		uint32_t *arr_size;    // array dimensions 
		int shared;            // 1 if image in shared memory
		int NBkw;              // number of keywords supported
		int CBSize;            // number of keywords supported
		char name[] = "flux";
		strcat(name,WFS_ID);
		// allocate memory for array of images
		flux_map = (IMAGE*) malloc(sizeof(IMAGE)*NB);
		
		//  array will be 2d
		n_axis = 2;
		
		// array size will be (NSUBX,NSUBX)
		arr_size = (uint32_t *) malloc(sizeof(uint32_t)*n_axis);
		arr_size[0] = N_SUBX;
		arr_size[1] = N_SUBX;
		
		// array will be float type
		// see file ImageStruct.h for list of supported types
		atype = _DATATYPE_FLOAT;
		
		// array will be in shared memory
		shared = 1;
		
		// allocate space for 10 keywords
		NBkw = 10; // TODO: check YON/OGU

		// no circular buffer
		CBSize = 1; // TODO: check YON/OGU

		// create slope vector in shared memory
		// TODO: do this using the connect_stream API instead
		ImageStreamIO_createIm(
			&flux_map[0], name, n_axis, 
			arr_size, atype, shared, NBkw, CBSize
		);
		free(arr_size);
	}
	
	// Main loop, wait for streams to be ready, then process them
	while (1)
	{
		int semindex = ImageStreamIO_getsemwaitindex(wfs_image, -1);
		ImageStreamIO_semwait(wfs_image, semindex);
		
		slope_map[0].md[0].write = 1; // set this flag to 1 when writing data
		flux_map[0].md[0].write = 1; // set this flag to 1 when writing data

		// ------ First pass ------
		// loop over every subap (valid or not), and do tasks subap-by-subap
		int n_valid = 0; // record number of valid subaps.
		for (int ii=0; ii<N_SUBX; ii++) {
			for(int jj=0; jj<N_SUBX; jj++) {
				float_t intensityx = 0.0;
				float_t intensityy = 0.0;
				float_t intensity = 0.0;
				
				// ----- flat field multiplication (TODO)
				for (int iii=0; iii<FOV_X; iii++){
					for (int jjj=0; jjj<FOV_X; jjj++){
						float pixel = wfs_image[0].array.F[wfs_image[0].md[0].size[0]*(jj*FOV_X+jjj)+FOV_X*ii+iii];
						pixel *= 1.0; // flat field value
						pixel -= 0.0; // background value
						if (COG_THRESH > -1.0) {
							// COG_THRESH less than zero implies (unsafe) no threshold
							// Try to avoid that, because you can end up with zeros in
							// the demoninator of the slope calculation.
							pixel -= COG_THRESH;
							if (pixel < 0.0) {
								pixel = 0.0;
							}
						}
						// TODO dead pixels interpolation
						intensityx += pixel * (float) iii;
						intensityy += pixel * (float) jjj;
						intensity += pixel;
					}
				}
				
				slope_map[0].array.F[jj*N_SUBX+ii] = intensityx /(intensity+1e-4);
				slope_map[0].array.F[jj*N_SUBX+ii+N_SUBX*N_SUBX] = intensityy/(intensity+1e-4);
				flux_map[0].array.F[jj*N_SUBX+ii] = intensity;
				n_valid += (wfs_valid[0].array.UI8[jj*N_SUBX+ii]==1) ? 1 : 0;
			}
		}
		ImageStreamIO_UpdateIm(slope_map);
		ImageStreamIO_UpdateIm(flux_map);

		// ------ Second pass ------
		// loop over all subaps again, and put their slopes in the slope_vec if 
		// it is a valid subap.
		
		slope_vec[0].md[0].write = 1; // set this flag to 1 when writing data
		
		int slopevec_idx = 0;
		for (int ii=0; ii<N_SUBX; ii++) {
			for(int jj=0; jj<N_SUBX; jj++) {
				if (wfs_valid[0].array.UI8[jj*N_SUBX+ii]==1) {
					slope_vec[0].array.F[slopevec_idx] = slope_map[0].array.F[jj*N_SUBX+ii];
					slope_vec[0].array.F[slopevec_idx+n_valid] = slope_map[0].array.F[jj*N_SUBX+ii+N_SUBX*N_SUBX];
					slopevec_idx += 1;
				}
			}
		}
		slopevec_idx = n_valid*2;
		while (slopevec_idx < (N_SUBX*N_SUBX)) {
			slope_vec[0].array.F[slopevec_idx] = 0.0;
			slopevec_idx += 1;
		}

		// ----- done

		// POST ALL SEMAPHORES
		ImageStreamIO_UpdateIm(slope_vec);
	}

	// If we ctrl-c to get out of the loop do we really need to do this?
	// When do these get called?
	free(wfs_image);
	free(slope_vec);
	free(flux_map);
	
	return 0;
}