/**
 * @file    centroids.c
 * @brief   basic centroider
 *
 * Calculate centroids from image stream
 */

#include "CommandLineInterface/CLIcore.h"

// Local variables pointers
static uint32_t *loopnumber;

static uint32_t *cntindex;
static long      fpi_cntindex = -1;

static uint32_t *cntindexmax;
static long      fpi_cntindexmax = -1;

static int64_t *ex0mode;
static long     fpi_ex0mode = -1;

static int64_t *ex1mode;
static long     fpi_ex1mode = -1;



static CLICMDARGDEF farg[] =
{
    {
        CLIARG_UINT32,
        ".loopnumber",
        "loop number",
        "1",
        CLIARG_VISIBLE_DEFAULT,
        (void **) &loopnumber,
        NULL
    },
    {
        CLIARG_UINT32,
        ".cntindex",
        "counter index",
        "5",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &cntindex,
        &fpi_cntindex
    },
    {
        CLIARG_UINT32,
        ".cntindexmax",
        "counter index max value",
        "100",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &cntindexmax,
        &fpi_cntindexmax
    },
    {
        CLIARG_ONOFF,
        ".option.ex0mode",
        "toggle0",
        "0",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &ex0mode,
        &fpi_ex0mode
    },
    {
        CLIARG_ONOFF,
        ".option.ex1mode",
        "toggle1 conditional on toggle0",
        "0",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &ex1mode,
        &fpi_ex1mode
    }
};

// Optional custom configuration setup
// Runs once at conf startup
//
// To use this function, set :
// CLIcmddata.FPS_customCONFsetup = customCONFsetup
// when registering function
// (see end of this file)
//
static errno_t customCONFsetup()
{
}

// Optional custom configuration checks
// Runs at every configuration check loop iteration
//
// To use this function, set :
// CLIcmddata.FPS_customCONFcheck = customCONFcheck
// when registering function
// (see end of this file)
//
static errno_t customCONFcheck()
{
    return RETURN_SUCCESS;
}


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



static errno_t streamprocess(
    IMGID *wfs_img, // wfs raw image
    IMGID *flux_map, // flux map
    IMGID *slope_map, // slope map
    IMGID *slope_vec, // slope vec
    IMGID *wfs_valid,
    IMGID *subap_lut_x,
    IMGID *subap_lut_y
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code

    // resolve imgpos
    resolveIMGID(wfs_img, ERRMODE_ABORT);

    // Create output image if needed
    imcreateIMGID(flux_map);
    imcreateIMGID(slope_map);
    imcreateIMGID(slope_vec);

    flux_map->md->write = 1;
    slope_map->md->write = 1;
    slope_vec->md->write = 1;

    const int N_SUBX = 32;
    const int FOV_X = 6;
    const float COG_THRESH = 0.0;

	uint32_t n_valid = 0;
	for (int i=0; i<N_SUBX*N_SUBX; i++){
		n_valid += (wfs_valid[0].im->array.UI8[i]==1) ? 1 : 0;
	}

	uint32_t valid_idx = 0;
	for (int i=0; i<N_SUBX*N_SUBX; i++){
		//if (wfs_valid[0].im->array.UI8[i]==0) {
		//	continue;
		//}
		// we're doing a valid subap
		float intensityx = 0.0;
		float intensityy = 0.0;
		float intensity = 0.0;
		uint32_t x0 = subap_lut_x[0].im->array.UI32[i];
		uint32_t y0 = subap_lut_y[0].im->array.UI32[i];

		for (int iii=0; iii<FOV_X; iii++){
			for (int jjj=0; jjj<FOV_X; jjj++){
				float pixel = wfs_img[0].im->array.F[wfs_img[0].md[0].size[0]*(y0+jjj)+x0+iii];
				pixel *= 1.0; // TODO: flat field value
				pixel -= 0.0; // TODO: background value
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
		slope_vec[0].im->array.F[valid_idx] = intensityx /(intensity+1e-4) - (float) FOV_X/2.0 + 0.5;;
		slope_vec[0].im->array.F[valid_idx+n_valid] = intensityy /(intensity+1e-4) - (float) FOV_X/2.0 + 0.5;;
		slope_map[0].im->array.F[i] = slope_vec[0].im->array.F[valid_idx];
		slope_map[0].im->array.F[i+N_SUBX*N_SUBX] = slope_vec[0].im->array.F[valid_idx+n_valid];
		flux_map[0].im->array.F[i] = intensity;
		valid_idx++;
	}
	for (int i=2*valid_idx; i<(2*N_SUBX*N_SUBX); i++){
		slope_vec[0].im->array.F[i] = 0.0;
	}
    
    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}




static errno_t compute_function()
{
    DEBUG_TRACE_FSTART();

    IMGID wfs_img;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "scmos%u_data", *loopnumber);
        wfs_img = stream_connect(name);
    }
    IMGID wfs_valid;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "wfsvalid%02u", *loopnumber);
        wfs_valid = stream_connect(name);
    }
    IMGID subap_lut_x;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "lut_xx_0_lgs%02u", *loopnumber);
        subap_lut_x = stream_connect(name);
    }
    IMGID subap_lut_y;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "lut_yy_0_lgs%02u", *loopnumber);
        subap_lut_y = stream_connect(name);
    }
    IMGID flux_map;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "flux%02u", *loopnumber);
        flux_map = stream_connect_create_2Df32(name, 32, 32);
    }
    IMGID slope_map;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "slopemap%02u", *loopnumber);
        slope_map = stream_connect_create_2Df32(name, 32, 64);
    }
    IMGID slope_vec;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "slopevec%02u", *loopnumber);
        slope_vec = stream_connect_create_2Df32(name, 1024, 1);
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
        WRITE_IMAGENAME(name, "scmos%u_data", *loopnumber);
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

        streamprocess(&wfs_img, &flux_map, &slope_map, &slope_vec,
                    &wfs_valid, &subap_lut_x, &subap_lut_y);
        //streamprocess(&in_img, &flux_map, &slope_map, &slope_vec,
        //            &wfs_valid, &subap_lut_x, &subap_lut_y);

        // stream is updated here, and not in the function called above, so that multiple
        // the above function can be chained with others
        processinfo_update_output_stream(processinfo, flux_map.ID);
        processinfo_update_output_stream(processinfo, slope_map.ID);
        processinfo_update_output_stream(processinfo, slope_vec.ID);
    }
    INSERT_STD_PROCINFO_COMPUTEFUNC_END

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}



INSERT_STD_FPSCLIfunctions



// Register function in CLI
errno_t
CLIADDCMD_ltaomod_centroider__streamprocess()
{
    CLIcmddata.FPS_customCONFsetup = customCONFsetup;
    CLIcmddata.FPS_customCONFcheck = customCONFcheck;

    INSERT_STD_CLIREGISTERFUNC

    return RETURN_SUCCESS;
}
