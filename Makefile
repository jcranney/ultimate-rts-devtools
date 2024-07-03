## gcc centroider.c /home/jcranney/isio/ImageStreamIO.c -lm -lpthread -I/usr/local/include/ImageStreamIO

# Define variables
CC = gcc
CFLAGS = -I/usr/local/include/ImageStreamIO -I/usr/local/milk-1.03.00/include
LDFLAGS = -lm -lpthread -L/usr/local/milk-1.03.00/lib # -lCLIcore -lmilkCOREMODmemory
LIB_SRC = $(HOME)/isio/ImageStreamIO.c

# Default target
all: centroider

# Compile the program
centroider: ./src/centroider.c $(LIB_SRC)
	mkdir -p ./build
	$(CC) ./src/centroider.c $(LIB_SRC) -o ./build/centroider.o $(CFLAGS) $(LDFLAGS)

# Clean up build files
clean:
	rm -rf ./build

.PHONY: all clean
