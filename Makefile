## gcc centroider.c /home/jcranney/isio/ImageStreamIO.c -lm -lpthread -I/usr/local/include/ImageStreamIO

# Define variables
CC = gcc
CFLAGS = -I/usr/local/include/ImageStreamIO -I/usr/local/milk-1.03.00/include

LDFLAGS = -lm -lpthread -L/usr/local/milk-1.03.00/lib # -lCLIcore -lmilkCOREMODmemory
LIB_SRC = /home/jcranney/isio/ImageStreamIO.c 

# Default target
all: centroider.o simulator.o

simulator.o: simulator.c $(LIB_SRC)
	$(CC) simulator.c $(LIB_SRC) -o simulator.o $(CFLAGS) $(LDFLAGS)

# Compile the program
centroider.o: centroider.c $(LIB_SRC)
	$(CC) centroider.c $(LIB_SRC) -o centroider.o $(CFLAGS) $(LDFLAGS)

# Clean up build files
clean:
	rm -f centroider.o simulator.o

.PHONY: all clean