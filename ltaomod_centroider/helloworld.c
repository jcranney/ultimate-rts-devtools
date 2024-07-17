/**
 * @file    helloworld.c
 * @brief   test file to learn procs, FPS, etc.
 *
 * paste the sum of an input image into the corner of an output image
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
    return RETURN_SUCCESS;
}


static CLICMDDATA CLIcmddata =
{
    "helloworld",
    "toy function for experimenting with milk",
    CLICMD_FIELDS_FPSPROC
};



// detailed help
static errno_t help_function()
{
    return RETURN_SUCCESS;
}



static errno_t helloworld(
    IMGID *inimg,
    IMGID *outimg
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code


    // resolve imgpos
    resolveIMGID(inimg, ERRMODE_ABORT);
    
    // Create output image if needed
    imcreateIMGID(outimg);
    
    outimg[0].md->write = 1;
    outimg[0].im->array.F[0] = 0.0;
    for (int i=0; i<inimg[0].size[0]*inimg[0].size[1]; i++){
	    outimg[0].im->array.F[0] = inimg[0].im->array.F[i];
    }
    


    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}

static errno_t compute_function()
{
    DEBUG_TRACE_FSTART();
    IMGID inimg;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "scmos%u_data", *loopnumber);
        inimg = stream_connect(name);
    }
    IMGID outimg;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "bob%u", *loopnumber);
        outimg = stream_connect_create_2Df32(name, 10, 10);
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

        helloworld(&inimg, &outimg);

        // stream is updated here, and not in the function called above, so that multiple
        // the above function can be chained with others
        processinfo_update_output_stream(processinfo, outimg.ID);

    }
    INSERT_STD_PROCINFO_COMPUTEFUNC_END

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}



INSERT_STD_FPSCLIfunctions



// Register function in CLI
errno_t
CLIADDCMD_ltaomod_centroider__helloworld()
{
    CLIcmddata.FPS_customCONFsetup = customCONFsetup;
    CLIcmddata.FPS_customCONFcheck = customCONFcheck;

    INSERT_STD_CLIREGISTERFUNC

    return RETURN_SUCCESS;
}
