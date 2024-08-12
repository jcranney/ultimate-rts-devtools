/**
 * @file    slopevec.c
 * @brief   assemble the slope vector
 *
 * In the case that many WFSs are running in parallel and the outputs are not
 * synchronised, this process synchronises them and updates the output shm
 * once all have arrived, or once a timer has expired (whichever occurs first).
 */

#include "CommandLineInterface/CLIcore.h"
#include "math.h"
#include <stdbool.h>
#include <sys/time.h>

// Local variables pointers
static uint32_t *wfs_flags; // binary mask for valid WFSs
static uint32_t *nsubx;
static uint32_t *nsuby;
static float *deadline;
const uint32_t MAX_NWFS=5;


static CLICMDARGDEF farg[] =
{
    {
        CLIARG_UINT32,
        ".wfsflags",
        "binary mask for valid WFSs (e.g., WFS1-4 = b11110 = 30)", 
        "30",
        CLIARG_HIDDEN_DEFAULT,
        (void **) &wfs_flags,
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
        CLIARG_FLOAT32,
        ".deadline",
        "how long to wait (in microseconds) before posting whole slove vector if any inputs are late",
        "200", 
        CLIARG_HIDDEN_DEFAULT,
        (void **) &deadline,
        NULL
    },
};

static errno_t customCONFsetup(){return RETURN_SUCCESS;}
static errno_t customCONFcheck(){return RETURN_SUCCESS;}

static CLICMDDATA CLIcmddata =
{
    "slopevec",
    "synchronises slope vector from WFS slopemaps",
    CLICMD_FIELDS_FPSPROC
};

// detailed help
static errno_t help_function()
{
    return RETURN_SUCCESS;
}

static errno_t syncslopevec(
    IMGID slope_maps[],  // local slope map
    IMGID *slope_vec,  // global slope vector
    uint32_t wfs_flags,  // index of wfs
    uint32_t nsubx,
    uint32_t nsuby,
    uint32_t deadline
)
{
    DEBUG_TRACE_FSTART();
    // custom stream process function code

    // resolve ids for chosen WFSs
    for (int i=0; i<MAX_NWFS; i++) {
        if (wfs_flags & (1 << i)) {
            resolveIMGID(&slope_maps[i], ERRMODE_ABORT);
        }
    }

    // build vector of flags indicating status of each WFS
    uint32_t ready_flags[MAX_NWFS];
    for (int i=0; i<MAX_NWFS; i++) {
        ready_flags[i] = 0;
    }

    // collect WFS slopemaps into slopevec then send them
    bool send = false; // 0 if not ready to send, 1 if ready.
    uint8_t started = 0; // flag to know if timer has started.
    struct timeval start, now;
    while (!send) {
        if (started == 1) {
            // assume we'll send until proven otherwise
            send = true;
            
            // check if any WFS is not ready
            for (int i=0; i<MAX_NWFS; i++) {
                if (wfs_flags & (1 << i)) {
                    send &= (ready_flags[i] > 0);
                }
            }
            if (send == 1) {
                break;
            }
            // at least one WFS isn't ready, has time expired?
            gettimeofday(&now,NULL);
            uint32_t elapsed = ( (now.tv_sec - start.tv_sec)*1000000L + now.tv_usec - start.tv_usec);
            // if so, then send them anyway and reset ready_flags.
            if (elapsed > deadline) {
                send = 1;
                printf("timeout!\n");
                break;
            }
        }
        // to be here means that either we haven't started, or we've started but
        // not finished and the deadline hasn't passed yet.
        int wfs_idx = 0;
        for (int i=0; i<MAX_NWFS; i++) {
            if (wfs_flags & (1 << i)) {
                // valid WFS
                if (ready_flags[i] == 0) {
                    // valid wfs index which hasn't been processed.
                    // Is it ready now?
                    if (ImageStreamIO_semtrywait(slope_maps[i].im, 0) == 0) {
                        while (ImageStreamIO_semtrywait(slope_maps[i].im, 0) == 0) {
                            // drive the semaphore to 0 (wait for trywait to return -1)
                        }
                        // yes, this one is ready.
                        // is this the first WFS that is ready?
                        if (started == 0) {
                            // if so, start the clock
                            gettimeofday(&start,NULL);
                            started = 1;
                        }
                        // update the slopevec with this wfs slopes.
                        int offset = wfs_idx*nsubx*nsuby*2;
                        for (int ii=0; ii<nsubx*nsuby*2; ii++){
                            slope_vec[0].im->array.F[ii+offset] = slope_maps[i].im->array.F[ii];
                        }
                        ready_flags[i] = 1;
                    }
                    // This wfs isn't ready yet - we'll check back in on it next
                    // time we're here. For now, we carry on.
                }
                wfs_idx++;
            }
        }
    }

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}



static errno_t compute_function()
{
    DEBUG_TRACE_FSTART();
    IMGID slope_maps[MAX_NWFS];
    int nwfs = 0;
    for (int i=0; i<MAX_NWFS; i++) {
        if (*wfs_flags & (1 << i)) {
            printf("wfs %d\n", i);
            char name[STRINGMAXLEN_STREAMNAME];
            WRITE_IMAGENAME(name, "slopemap%d", i);
            slope_maps[i] = stream_connect(name);
            nwfs++;
        }
    }

    IMGID slope_vec;
    {
        char name[STRINGMAXLEN_STREAMNAME];
        WRITE_IMAGENAME(name, "slopevec");
        slope_vec = stream_connect_create_2Df32(name, (*nsubx)*(*nsuby)*2*nwfs, 1); // global slope vector
    }

    list_image_ID();

    printf(" COMPUTE Flags = %ld\n", CLIcmddata.cmdsettings->flags);
    INSERT_STD_PROCINFO_COMPUTEFUNC_INIT

    // custom initialization
    printf(" COMPUTE Flags = %ld\n", CLIcmddata.cmdsettings->flags);
    if(CLIcmddata.cmdsettings->flags & CLICMDFLAG_PROCINFO)
    {
        // procinfo is accessible here
        CLIcmddata.cmdsettings->procinfo_loopcntMax = -1;
        CLIcmddata.cmdsettings->triggermode = 0;
    }

    // If custom initialization with access to procinfo is not required
    // then replace
    // INSERT_STD_PROCINFO_COMPUTEFUNC_INIT
    // INSERT_STD_PROCINFO_COMPUTEFUNC_LOOPSTART
    // With :
    // INSERT_STD_PROCINFO_COMPUTEFUNC_START

    INSERT_STD_PROCINFO_COMPUTEFUNC_LOOPSTART
    {
        syncslopevec(slope_maps, &slope_vec, *wfs_flags, *nsubx, *nsuby, *deadline);
        processinfo_update_output_stream(processinfo, slope_vec.ID);
    }
    INSERT_STD_PROCINFO_COMPUTEFUNC_END

    DEBUG_TRACE_FEXIT();
    return RETURN_SUCCESS;
}



INSERT_STD_FPSCLIfunctions



// Register function in CLI
errno_t
CLIADDCMD_ltaomod_centroider__syncslopevec()
{
    CLIcmddata.FPS_customCONFsetup = customCONFsetup;
    CLIcmddata.FPS_customCONFcheck = customCONFcheck;

    INSERT_STD_CLIREGISTERFUNC

    return RETURN_SUCCESS;
}
