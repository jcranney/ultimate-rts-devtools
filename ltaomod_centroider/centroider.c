/**
 * @file    centroids.c
 * @brief   basic centroider
 *
 * Calculate centroids from image stream
 */

#include "CommandLineInterface/CLIcore.h"

// Local variables pointers

static char *in_im_name;
static char *wfs_valid_name;
static char *subap_lut_x_name;
static char *subap_lut_y_name;
long fpi_in_im_name;
long fpi_wfs_valid_name;
long fpi_subap_lut_x_name;
long fpi_subap_lut_y_name;

static LOCVAR_OUTIMG2D fluxmap_im;
//static LOCVAR_OUTIMG2D slopemap_im;
//static LOCVAR_OUTIMG2D slopevec_im;


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
        CLIARG_IMG,
        ".in_img",
        "input wfs image",
        "scmos1_data",
        CLIARG_VISIBLE_DEFAULT,
        (void **) &in_im_name,
        &fpi_in_im_name
    },
    {
        CLIARG_IMG,
        ".wfs_valid_name",
        "valid subaperture map",
        "wfs_valid01",
        CLIARG_VISIBLE_DEFAULT,
        (void **) &wfs_valid_name,
        NULL
    },
    {
        CLIARG_IMG,
        ".subap_lut_x_name",
        "valid subaperture pixel LUT",
        "subap_lut_x01",
        CLIARG_VISIBLE_DEFAULT,
        (void **) &subap_lut_x_name,
        NULL
    },
    {
        CLIARG_IMG,
        ".subap_lut_y_name",
        "valid subaperture pixel LUT",
        "subap_lut_y01",
        CLIARG_VISIBLE_DEFAULT,
        (void **) &subap_lut_y_name,
        NULL
    },
    FARG_OUTIM2D(fluxmap_im),
    //FARG_OUTIM2D(slopemap_im),
    //FARG_OUTIM2D(slopevec_im),
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
    // increment counter at every configuration check
    *cntindex = *cntindex + 1;

    if(*cntindex >= *cntindexmax)
    {
        *cntindex = 0;
    }

    return RETURN_SUCCESS;
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
    if(data.fpsptr != NULL)
    {
        if(data.fpsptr->parray[fpi_ex0mode].fpflag & FPFLAG_ONOFF)  // ON state
        {
            data.fpsptr->parray[fpi_ex1mode].fpflag |= FPFLAG_USED;
            data.fpsptr->parray[fpi_ex1mode].fpflag |= FPFLAG_VISIBLE;
        }
        else // OFF state
        {
            data.fpsptr->parray[fpi_ex1mode].fpflag &= ~FPFLAG_USED;
            data.fpsptr->parray[fpi_ex1mode].fpflag &= ~FPFLAG_VISIBLE;
        }

        // increment counter at every configuration check
        *cntindex = *cntindex + 1;

        if(*cntindex >= *cntindexmax)
        {
            *cntindex = 0;
        }

    }

    return RETURN_SUCCESS;
}


static CLICMDDATA CLIcmddata =
{
    "centroider",
    "calculate centroids from WFS image",
    CLICMD_FIELDS_DEFAULTS
};



// detailed help
static errno_t help_function()
{
    return RETURN_SUCCESS;
}



static errno_t streamprocess(
    IMGID *wfs_img, // wfs raw image
    IMGID *flux_map, // flux map
//    IMGID *slope_map, // slope map
//    IMGID *slope_vec, // slope vec
    IMGID *wfs_valid,
    IMGID *subap_lut_x,
    IMGID *subap_lut_y
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code


    // resolve imgpos
    resolveIMGID(wfs_img, ERRMODE_ABORT);
    imcreateIMGID(flux_map);

    const int N_SUBX = 32;
    const int FOV_X = 6;
    const float COG_THRESH = 0.0;

	//uint32_t n_valid = 0;
	//for (int i=0; i<N_SUBX*N_SUBX; i++){
	//	n_valid += (wfs_valid[0].im->array.UI8[i]==1) ? 1 : 0;
	//}

	//uint32_t valid_idx = 0;
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
		//slope_vec[0].im->array.F[valid_idx] = intensityx /(intensity+1e-4) - (float) FOV_X/2.0 + 0.5;;
		//slope_vec[0].im->array.F[valid_idx+n_valid] = intensityy /(intensity+1e-4) - (float) FOV_X/2.0 + 0.5;;
		//slope_map[0].im->array.F[i] = slope_vec[0].im->array.F[valid_idx];
		//slope_map[0].im->array.F[i+N_SUBX*N_SUBX] = slope_vec[0].im->array.F[valid_idx+n_valid];
		flux_map[0].im->array.F[i] = intensity;
		//valid_idx++;
	}
	//for (int i=2*valid_idx; i<(2*N_SUBX*N_SUBX); i++){
		//slope_vec[0].im->array.F[i] = 0.0;
	//}
    
    //for (int i=0; i<wfsimg[0].size[0]*wfsimg[0].size[1]; i++){
	//    fluxmap[0].im->array.F[0] = wfsimg[0].im->array.F[i];
    //}
    
    // Create output image if needed
    //imcreateIMGID(slope_map);
    //imcreateIMGID(slope_vec);


    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}




static errno_t compute_function()
{
    DEBUG_TRACE_FSTART();

    IMGID in_img = mkIMGID_from_name(in_im_name);
    resolveIMGID(&in_img, ERRMODE_ABORT);

    IMGID wfs_valid = mkIMGID_from_name(wfs_valid_name);
    resolveIMGID(&wfs_valid, ERRMODE_ABORT);
    
    IMGID subap_lut_x = mkIMGID_from_name(subap_lut_x_name);
    resolveIMGID(&subap_lut_x, ERRMODE_ABORT);
    
    IMGID subap_lut_y = mkIMGID_from_name(subap_lut_y_name);
    resolveIMGID(&subap_lut_y, ERRMODE_ABORT);

    // link/create output image/stream
    FARG_OUTIM2DCREATE(fluxmap_im, flux_map, _DATATYPE_FLOAT);
    //FARG_OUTIM2DCREATE(slopemap_im, slope_map, _DATATYPE_FLOAT);
    //FARG_OUTIM2DCREATE(slopevec_im, slope_vec, _DATATYPE_FLOAT);

    printf(" COMPUTE Flags = %ld\n", CLIcmddata.cmdsettings->flags);
    INSERT_STD_PROCINFO_COMPUTEFUNC_INIT

    // custom initialization
    printf(" COMPUTE Flags = %ld\n", CLIcmddata.cmdsettings->flags);
    if(CLIcmddata.cmdsettings->flags & CLICMDFLAG_PROCINFO)
    {
        // procinfo is accessible here
    }

    // If custom initialization with access to procinfo is not required
    // then replace
    // INSERT_STD_PROCINFO_COMPUTEFUNC_INIT
    // INSERT_STD_PROCINFO_COMPUTEFUNC_LOOPSTART
    // With :
    // INSERT_STD_PROCINFO_COMPUTEFUNC_START

    INSERT_STD_PROCINFO_COMPUTEFUNC_LOOPSTART
    {

        streamprocess(&in_img, &flux_map,
                    &wfs_valid, &subap_lut_x, &subap_lut_y);
        //streamprocess(&in_img, &flux_map, &slope_map, &slope_vec,
        //            &wfs_valid, &subap_lut_x, &subap_lut_y);

        // stream is updated here, and not in the function called above, so that multiple
        // the above function can be chained with others
        processinfo_update_output_stream(processinfo, flux_map.ID);
        //processinfo_update_output_stream(processinfo, slope_map.ID);
        //processinfo_update_output_stream(processinfo, slope_vec.ID);

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
