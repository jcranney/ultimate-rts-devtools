/**
 * @file    centroids.c
 * @brief   basic centroider
 *
 * Calculate centroids from image stream
 */

#include "CommandLineInterface/CLIcore.h"
#include "math.h"

// Local variables pointers
static uint32_t *wfsnumber;
static uint32_t *nsubx;
static uint32_t *nsuby;
static uint32_t *fovx;
static uint32_t *fovy;
static float *thresh;
static uint32_t *bgnpix;
static float *fluxthresh;


static CLICMDARGDEF farg[] =
{
    {
        CLIARG_UINT32,
        ".wfsnumber",
        "wfs number",
        "1",
        CLIARG_VISIBLE_DEFAULT,
        (void **) &wfsnumber,
        NULL
    },
    {
        CLIARG_UINT32,
        ".nsubx",
        "number of subapertures in x-dimension",
        "32",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &nsubx,
        NULL
    },
    {
        CLIARG_UINT32,
        ".nsuby",
        "number of subapertures in y-dimension",
        "32",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &nsuby,
        NULL
    },
    {
        CLIARG_UINT32,
        ".fovx",
        "FOV of each subaperture in pixels (x-dim)",
        "6",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &fovx,
        NULL
    },
    {
        CLIARG_UINT32,
        ".fovy",
        "FOV of each subaperture in pixels (y-dim)",
        "6",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &fovy,
        NULL
    },
    {
        CLIARG_FLOAT32,
        ".cogthresh",
        "threshold for tcog",
        "0.0",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &thresh,
        NULL
    },
    {
        CLIARG_UINT32,
        ".bgnpix",
        "number of pixels to take from the left and right for extra background subtraction",
        "0",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &bgnpix,
        NULL
    },
    {
        CLIARG_FLOAT32,
        ".fluxthresh",
        "flux threshold (as ratio of brightest subaperture) for determining valid subapertures",
        "0.3", // 0.0 means that we accept any subaperture with flux greater than 0.0
        CLIARG_HIDDEN_DEFAULT,
        (void **) &fluxthresh,
        NULL
    },
};

static errno_t customCONFsetup(){return RETURN_SUCCESS;}
static errno_t customCONFcheck(){return RETURN_SUCCESS;}

static CLICMDDATA CLIcmddata =
{
    "centroider",
    "calculate centroids from WFS image",
    CLICMD_FIELDS_FPSPROC
};

// detailed help
static errno_t help_function()
{
    return RETURN_SUCCESS;
}

static errno_t docentroids(
    IMGID *wfs_img,  // wfs raw image
    IMGID *flux_map,  // flux map
    IMGID *slope_map,  // slope map
    IMGID *subap_lut_x,  // pixel position (x) of centre of subap
    IMGID *subap_lut_y,  // pixel position (y) of centre of subap
    //IMGID *wfs_flat,  // pixel position (y) of centre of subap
    IMGID *wfs_bg, // pixel position (y) of centre of subap
    float thresh,
    uint32_t fovx,
    uint32_t fovy,
    uint32_t nsubx,
    uint32_t nsuby,
    uint32_t bgnpix
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code

    // resolve imgpos
    resolveIMGID(wfs_img, ERRMODE_ABORT);

    // Create output image if needed
    imcreateIMGID(flux_map);
    imcreateIMGID(slope_map);

    flux_map->md->write = 1;
    slope_map->md->write = 1;

    float bg_row[wfs_img[0].md[0].size[1]];
    for (int row=0; row<wfs_img[0].md[0].size[1]; row++){
        bg_row[row] = 0.0;
        for (int column_offset=0; column_offset<bgnpix; column_offset++){
            bg_row[row] += wfs_img[0].im->array.UI16[wfs_img[0].md[0].size[0]*(row)+column_offset] - 
                           wfs_bg[0].im->array.F[wfs_img[0].md[0].size[0]*(row)+column_offset];
            bg_row[row] += wfs_img[0].im->array.UI16[wfs_img[0].md[0].size[0]*(row+1)-column_offset-1] -
                           wfs_bg[0].im->array.F[wfs_img[0].md[0].size[0]*(row+1)-column_offset-1];
        }
        if (bgnpix>0) {
            bg_row[row] /= (2*bgnpix);
        }   
    }
    
	for (int i=0; i<nsubx*nsuby; i++){
		float intensityx = 0.0;
		float intensityy = 0.0;
		float intensity = 0.0;
		float xc = subap_lut_x[0].im->array.F[i];
	    float yc = subap_lut_y[0].im->array.F[i];
        uint32_t x0 = round(xc - fovx/2);
        uint32_t y0 = round(yc - fovy/2);
        float x_offset = xc - x0 - 0.5;
        float y_offset = yc - y0 - 0.5;

		for (int iii=0; iii<fovx; iii++){
			for (int jjj=0; jjj<fovy; jjj++){
                uint32_t idx = wfs_img[0].md[0].size[0]*(y0+jjj)+x0+iii;
				float pixel = wfs_img[0].im->array.UI16[idx];
                //pixel *= wfs_flat[0].im->array.F[idx];
                pixel -= wfs_bg[0].im->array.F[idx];
				pixel -= bg_row[y0+jjj];
                if (thresh > -1.0) {
					pixel -= thresh;
					if (pixel < 0.0) {
						pixel = 0.0;
					}
				}
				intensityx += pixel * (iii - x_offset);
				intensityy += pixel * (jjj - y_offset);
				intensity += pixel;
			}
		}
		slope_map[0].im->array.F[i] = intensityx/(intensity+1e-1);
		slope_map[0].im->array.F[i+nsubx*nsuby] = intensityy/(intensity+1e-1);
		flux_map[0].im->array.F[i] = intensity;
	}
    
    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}


static errno_t reducemeasurements(
    IMGID *flux_map,  // flux map
    IMGID *slope_map,  // slope map
    uint32_t nsubx,
    uint32_t nsuby,
    float fluxthresh
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code

    // resolve imgpos
    resolveIMGID(flux_map, ERRMODE_ABORT);
    resolveIMGID(slope_map, ERRMODE_ABORT);

    // not sure if -infty is safe, so let's just take the 0th subaperture flux
    // as initial "maximum"
    float max_flux = flux_map[0].im->array.F[0];
    uint32_t num_valid = 0;
	for (int i=0; i<nsubx*nsuby; i++){
        max_flux = fmax(max_flux, flux_map[0].im->array.F[i]);
    }
    float thresh = fluxthresh*max_flux;

    float tt_x = 0.0;
    float tt_y = 0.0;
	for (int i=0; i<nsubx*nsuby; i++){
        if (flux_map[0].im->array.F[i] >= thresh) {
            num_valid += 1;
            tt_x += slope_map[0].im->array.F[i];
            tt_y += slope_map[0].im->array.F[i+nsubx*nsuby];
        }
    }
    if (num_valid > 0) {
        tt_x /= num_valid;
        tt_y /= num_valid;
    }
    printf("%5u  %8.3f  %8.3f\n", num_valid, tt_x, tt_y);

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}

static errno_t try_collate(
    IMGID *slope_map,  // local slope map
    IMGID *slope_vec,  // global slope vector
    uint32_t wfsnumber,  // index of wfs
    uint32_t nsubx,
    uint32_t nsuby
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code


    uint32_t offset;
    switch (wfsnumber) {
        case 1:
            offset = (nsubx*nsuby*2)*0;
            break;
        case 2:
            offset = (nsubx*nsuby*2)*1;
            break;
        case 3:
            offset = (nsubx*nsuby*2)*2;
            break;
        case 4:
            offset = (nsubx*nsuby*2)*3;
            break;
        default:
            // this wfs is not used, skip
            return RETURN_SUCCESS;
    }

    // resolve imgpos
    resolveIMGID(slope_map, ERRMODE_ABORT);
    imcreateIMGID(slope_vec);
    slope_vec->md->write = 1;
    
    for (int i=0; i<nsubx*nsuby*2; i++){
        slope_vec[0].im->array.F[i+offset] = slope_map[0].im->array.F[i];
    }

    ImageStreamIO_UpdateIm(slope_vec->im);
    // leaving the synchronisation signal for discussion with Olivier + Yoshito
    // but thinking about the logic - something like this could work:
    /*
    
    imcreateIMGID(posted_slopes);
    posted_slopes->md->write = 1;

    posted_slopes[wfsnumber] += 1;

    bool slopes_ready = true;
    slopes_ready &= (posted_slopes[1] > 0)
    slopes_ready &= (posted_slopes[2] > 0)
    slopes_ready &= (posted_slopes[3] > 0)
    slopes_ready &= (posted_slopes[4] > 0)

    if slopes_ready {
        posted_slopes[1] = 0;
        posted_slopes[2] = 0;
        posted_slopes[3] = 0;
        posted_slopes[4] = 0;
        // -- send them to RTS --
    } else {

    }


    processinfo_update_output_stream(processinfo, posted_slopes.ID);
    */

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}



static errno_t compute_function()
{
    DEBUG_TRACE_FSTART();

    IMGID wfs_img;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "scmos%u_data", *wfsnumber);
        wfs_img = stream_connect(name);
    }
    IMGID subap_lut_x;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "lutx%01u", *wfsnumber);
        subap_lut_x = stream_connect(name);
    }
    IMGID subap_lut_y;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "luty%01u", *wfsnumber);
        subap_lut_y = stream_connect(name);
    }
    /*
    IMGID wfs_flat;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "wfsflat%02u", *wfsnumber);
        wfs_flat = stream_connect(name);
    }
    */
    IMGID wfs_bg;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "scmos%01u_bg", *wfsnumber);
        wfs_bg = stream_connect(name);
    }
    IMGID flux_map;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "flux%01u", *wfsnumber);
        flux_map = stream_connect_create_2Df32(name, 32, 32);
    }
    IMGID slope_map;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "slopemap%01u", *wfsnumber);
        slope_map = stream_connect_create_2Df32(name, 32, 64);
    }
    IMGID slope_vec;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "slopevec");
        slope_vec = stream_connect_create_2Df32(name, 32*32*2*4, 1); // global slope vector
    }
    list_image_ID();

    printf(" COMPUTE Flags = %ld\n", CLIcmddata.cmdsettings->flags);
    INSERT_STD_PROCINFO_COMPUTEFUNC_INIT

    // custom initialization
    printf(" COMPUTE Flags = %ld\n", CLIcmddata.cmdsettings->flags);
    if(CLIcmddata.cmdsettings->flags & CLICMDFLAG_PROCINFO)
    {
        // procinfo is accessible here
        CLIcmddata.cmdsettings->triggermode = 3;
        CLIcmddata.cmdsettings->procinfo_loopcntMax = -1;
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "scmos%u_data", *wfsnumber);
        strcpy(CLIcmddata.cmdsettings->triggerstreamname, name);
    }

    // If custom initialization with access to procinfo is not required
    // then replace
    // INSERT_STD_PROCINFO_COMPUTEFUNC_INIT
    // INSERT_STD_PROCINFO_COMPUTEFUNC_LOOPSTART
    // With :
    // INSERT_STD_PROCINFO_COMPUTEFUNC_START

    INSERT_STD_PROCINFO_COMPUTEFUNC_LOOPSTART
    {

        docentroids(&wfs_img, &flux_map, &slope_map,
                    &subap_lut_x, &subap_lut_y, &wfs_bg,
                    *thresh, *fovx, *fovy, *nsubx, *nsuby, *bgnpix);
        processinfo_update_output_stream(processinfo, flux_map.ID);
        processinfo_update_output_stream(processinfo, slope_map.ID);
        try_collate(&slope_map, &slope_vec, *wfsnumber, *nsubx, *nsuby);
        reducemeasurements(&flux_map, &slope_map, *nsubx, *nsuby, *fluxthresh);
    }
    INSERT_STD_PROCINFO_COMPUTEFUNC_END

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}



INSERT_STD_FPSCLIfunctions



// Register function in CLI
errno_t
CLIADDCMD_ltaomod_centroider__docentroids()
{
    CLIcmddata.FPS_customCONFsetup = customCONFsetup;
    CLIcmddata.FPS_customCONFcheck = customCONFcheck;

    INSERT_STD_CLIREGISTERFUNC

    return RETURN_SUCCESS;
}
