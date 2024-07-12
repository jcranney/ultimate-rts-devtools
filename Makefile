## gcc centroider.c /home/jcranney/isio/ImageStreamIO.c -lm -lpthread -I/usr/local/include/ImageStreamIO

# Define variables
CC = gcc
CFLAGS = -I/usr/local/include/ImageStreamIO #-I/usr/local/milk-1.03.00/include
LDFLAGS = -lm -lpthread # -L/usr/local/milk-1.03.00/lib  -lCLIcore -lmilkCOREMODmemory
LIB_SRC = $(HOME)/isio/ImageStreamIO.c

# Default target
all: centroider

# Compile the program
centroider: ./src/centroider.c $(LIB_SRC)
	mkdir -p ./build
	$(CC) ./src/centroider.c $(LIB_SRC) -o ./build/centroider.o $(CFLAGS) $(LDFLAGS) -O3
	$(CC) ./src/centroider1.c $(LIB_SRC) -o ./build/centroider1.o $(CFLAGS) $(LDFLAGS) -O3
	$(CC) ./src/centroider2.c $(LIB_SRC) -o ./build/centroider2.o $(CFLAGS) $(LDFLAGS) -O3
	$(CC) ./src/centroider3.c $(LIB_SRC) -o ./build/centroider3.o $(CFLAGS) $(LDFLAGS) -O3
	$(CC) ./src/centroider4.c $(LIB_SRC) -o ./build/centroider4.o $(CFLAGS) $(LDFLAGS) -O3
	$(CC) ./src/centroider5.c $(LIB_SRC) -o ./build/centroider5.o $(CFLAGS) $(LDFLAGS) -O3
	ln -fs ./build/centroider.o ./centroider
	ln -fs ./build/centroider1.o ./centroider1
	ln -fs ./build/centroider2.o ./centroider2
	ln -fs ./build/centroider3.o ./centroider3
	ln -fs ./build/centroider4.o ./centroider4
	ln -fs ./build/centroider5.o ./centroider5

# Clean up build files
clean:
	rm -rf ./build
	rm centroider
	rm centroider1
	rm centroider2
	rm centroider3
	rm centroider4
	rm centroider5

.PHONY: all clean
