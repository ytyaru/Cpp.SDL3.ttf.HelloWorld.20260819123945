#!/usr/bin/env python3
import os
import sys
import datetime

def main():
    # タイムスタンプ取得
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    project_dir = f"sdl3-ttf-{timestamp}"
    
    os.makedirs(project_dir, exist_ok=True)
    
    # 1. CMakeLists.txt
    cmakelists_content = """cmake_minimum_required(VERSION 3.25)
project(sdl3_ime_demo C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(FetchContent)

set(DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
set(SDLTTF_VENDORED ON CACHE BOOL "" FORCE)

FetchContent_Declare(
    SDL3
    GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
    GIT_TAG release-3.4.14
)

FetchContent_Declare(
    SDL3_ttf
    GIT_REPOSITORY https://github.com/libsdl-org/SDL_ttf.git
    GIT_TAG release-3.2.2
)

FetchContent_MakeAvailable(SDL3 SDL3_ttf)

add_executable(sdl3_ime_demo main.c)
target_link_libraries(sdl3_ime_demo PRIVATE SDL3::SDL3 SDL3_ttf::SDL3_ttf)
"""

    # 2. build.sh
    build_sh_content = """#!/bin/bash
cd "$(dirname "$0")"
mkdir -p build
cd build
cmake -G Ninja ..
ninja -j2
"""

    # 3. main.c
    main_c_content = """#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>
#include <stdio.h>
#include <stdbool.h>

int main(int argc, char* argv[]) {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        SDL_Log("SDL_Init Error: %s", SDL_GetError());
        return 1;
    }

    if (!TTF_Init()) {
        SDL_Log("TTF_Init Error: %s", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_Window* window = SDL_CreateWindow("SDL3 IME Demo", 800, 600, SDL_WINDOW_RESIZABLE);
    if (!window) {
        SDL_Log("SDL_CreateWindow Error: %s", SDL_GetError());
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    SDL_Renderer* renderer = SDL_CreateRenderer(window, NULL);
    if (!renderer) {
        SDL_Log("SDL_CreateRenderer Error: %s", SDL_GetError());
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    const char* main_font_path = "/home/pi/.fonts/UDEVGothicJPDOC-Regular.ttf";
    const char* fallback_font_path = "/home/pi/.fonts/UDEVGothicNF-Regular.ttf";

    TTF_Font* font = TTF_OpenFont(main_font_path, 24);
    TTF_Font* fallback_font = TTF_OpenFont(fallback_font_path, 24);

    if (font && fallback_font) {
        if (!TTF_AddFallbackFont(font, fallback_font)) {
            SDL_Log("Warning: Failed to add fallback font");
        }
    } else {
        SDL_Log("Warning: One or both fonts could not be loaded. Paths checked:");
        SDL_Log("Main: %s", main_font_path);
        SDL_Log("Fallback: %s", fallback_font_path);
    }

    SDL_StartTextInput(window);

    bool quit = false;
    SDL_Event event;
    char text[1024] = {0};

    while (!quit) {
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) {
                quit = true;
            } else if (event.type == SDL_EVENT_TEXT_EDITING) {
                printf("IME Editing (composition): %s (start: %d, len: %d)\\n", 
                       event.edit.text, event.edit.start, event.edit.length);
            } else if (event.type == SDL_EVENT_TEXT_INPUT) {
                printf("IME Input (confirmed): %s\\n", event.text.text);
                snprintf(text, sizeof(text), "%s", event.text.text);
            }
        }

        SDL_SetRenderDrawColor(renderer, 30, 30, 30, 255);
        SDL_RenderClear(renderer);
        SDL_RenderPresent(renderer);
        SDL_Delay(16);
    }

    if (font) TTF_CloseFont(font);
    if (fallback_font) TTF_CloseFont(fallback_font);

    SDL_StopTextInput(window);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    TTF_Quit();
    SDL_Quit();
    return 0;
}
"""

    # Write files
    with open(os.path.join(project_dir, "CMakeLists.txt"), "w") as f:
        f.write(cmakelists_content)
        
    with open(os.path.join(project_dir, "build.sh"), "w") as f:
        f.write(build_sh_content)
    os.chmod(os.path.join(project_dir, "build.sh"), 0o755)
        
    with open(os.path.join(project_dir, "main.c"), "w") as f:
        f.write(main_c_content)
        
    print(f"Project structure successfully created in: {project_dir}")

if __name__ == "__main__":
    main()
