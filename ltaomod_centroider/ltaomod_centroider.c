/**
 * @file    ltaomod_centroider.c
 * @brief   example milk module
 *
 * milk module source code template\n
 * Demonstates how to add modules to milk and connect functions.\n
 *
 *
 * To compile with module :
 * > cd _build
 * > cmake .. -DEXTRAMODULES="ltaomod_centroider" -DINSTALLMAKEDEFAULT=ON
 *
 *
 * To load, type "mload milkltaomodcentroider" in CLI\n
 *
 *
 *  Files
 *
 * - CMakeLists.txt         : cmake input file for module
 *
 * - ltaomod_centroider.c  : module main C file, includes binding code to milk
 * - ltaomod_centroider.h  : function prototypes to be included by other modules
 *
 *
 * Several examples are provided to demonstrate code features.
 * Each example builds on the previous one(s), demonstrating additional capabilities.
 *
 * ## Simple function example
 *
 * Simple function example. No FPS, no processinfo.
 *
 * Files:
 * - simplefunc.c
 * - simplefunc.h
 *
 *
 * ## Function parameter structure (FPS) example
 *
 *
 *
 *
 * - create_example_image.c : source code, .c file
 * - create_example_image.h : source code, .h file
 *
 */

#define _GNU_SOURCE

/* ================================================================== */
/* ================================================================== */
/*  MODULE INFO                                                       */
/* ================================================================== */
/* ================================================================== */

// module default short name
// all CLI calls to this module functions will be <shortname>.<funcname>
// if set to "", then calls use <funcname>
#define MODULE_SHORTNAME_DEFAULT "ltao"

// Module short description
#define MODULE_DESCRIPTION "Example module: template for creating new modules"

/* ================================================================== */
/* ================================================================== */
/*  HEADER FILES                                                      */
/* ================================================================== */
/* ================================================================== */

#include "CommandLineInterface/CLIcore.h"

//
// Forward declarations are required to connect CLI calls to functions
// If functions are in separate .c files, include here the corresponding .h files
//
#include "centroider.h"
#include "helloworld.h"

//#include "create_example_image.h"
//#include "stream_process_loop_simple.h"

//#include "updatestreamloop_brief.h"

/* ================================================================== */
/* ================================================================== */
/*  INITIALIZE LIBRARY                                                */
/* ================================================================== */
/* ================================================================== */

// Module initialization macro in CLIcore.h
// macro argument defines module name for bindings
//
INIT_MODULE_LIB(ltaomod_centroider)

/**
 * @brief Initialize module CLI
 *
 * CLI entries are registered: CLI call names are connected to CLI functions.\n
 * Any other initialization is performed\n
 *
 */
static errno_t init_module_CLI()
{

    //CLI_CMD_CONNECT("func1", "create_image_with_value");

    //create_example_image_addCLIcmd();
    //stream_process_loop_simple_addCLIcmd();

    //	ltaomod_centroider__updatestreamloop_addCLIcmd();

    CLIADDCMD_ltaomod_centroider__simplefunc();
    CLIADDCMD_ltaomod_centroider__simplefunc_FPS();
    CLIADDCMD_ltaomod_centroider__updatestreamloop();
    CLIADDCMD_ltaomod_centroider__streamprocess();
    CLIADDCMD_ltaomod_centroider__helloworld();

    // optional: add atexit functions here

    return RETURN_SUCCESS;
}
