# Makefile for Buffer Overflow Challenge

CC = gcc
CFLAGS = -m64 -fno-stack-protector -z execstack -no-pie -g
TARGET = chall

all: $(TARGET)

$(TARGET): chall.c
	$(CC) $(CFLAGS) -o $(TARGET) chall.c
	@echo "✅ Binary compiled successfully"
	@echo "🔍 Checking security features:"
	@checksec $(TARGET) || echo "Install checksec to see security features"

clean:
	rm -f $(TARGET)

# 安裝到 files 和 docker 目錄
install: $(TARGET)
	@mkdir -p ../files ../docker
	@cp $(TARGET) ../files/
	@cp $(TARGET) ../docker/
	@echo "✅ Installed to ../files/ and ../docker/"

# 完整建置（編譯 + 安裝）
build: all install
	@echo "🚀 Build complete!"

.PHONY: all clean install build
