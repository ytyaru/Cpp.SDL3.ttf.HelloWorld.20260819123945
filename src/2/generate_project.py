#!/usr/bin/env python3
import os
import sys
import datetime

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    project_dir = f"sdl3-ttf-{timestamp}"
    
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "build"), exist_ok=True)
    
    # 1. CMakeLists.txt
    cmakelists_content = """cmake_minimum_required(VERSION 3.25)
project(sdl3_ime_demo C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(FetchContent)

set(DOWNLOAD_EXTRACT_TIMESTAMP TRUE)

FetchContent_Declare(
    SDL3
    GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
    GIT_TAG release-3.4.14
)

set(SDLTTF_VENDORED ON CACHE BOOL "" FORCE)

FetchContent_Declare(
    sdl3_ttf
    GIT_REPOSITORY https://github.com/libsdl-org/SDL_ttf.git
    GIT_TAG release-3.2.2
)

FetchContent_MakeAvailable(SDL3 sdl3_ttf)

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
    main_c_content = """#define _GNU_SOURCE
#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>

#define WINDOW_WIDTH 800
#define WINDOW_HEIGHT 600

char confirmed_text[1024] = "日本語入力テスト: ";
char composition_text[512] = "";

int main(int argc, char* argv[]) {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        SDL_Log("SDL_Init Error: %s\\n", SDL_GetError());
        return 1;
    }
    if (!TTF_Init()) {
        SDL_Log("TTF_Init Error: %s\\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_Window* window = SDL_CreateWindow("SDL3 IME & Font Fallback Demo", WINDOW_WIDTH, WINDOW_HEIGHT, 0);
    if (!window) {
        SDL_Log("Window Creation Error: %s\\n", SDL_GetError());
        TTF_Quit();
        SDL_Quit();
        return 1;
    }
    SDL_Renderer* renderer = SDL_CreateRenderer(window, NULL);
    if (!renderer) {
        SDL_Log("Renderer Creation Error: %s\\n", SDL_GetError());
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    const char* main_font_path = "/home/pi/.fonts/UDEVGothicJPDOC-Regular.ttf";
    const char* fallback_font_path = "/home/pi/.fonts/UDEVGothicNF-Regular.ttf";

    TTF_Font* font = TTF_OpenFont(main_font_path, 24);
    TTF_Font* fallback_font = TTF_OpenFont(fallback_font_path, 24);

    if (!font) {
        SDL_Log("Warning: Failed to load main font. trying fallback directly.\\n");
        font = fallback_font;
        fallback_font = NULL;
    } else if (fallback_font) {
        if (!TTF_AddFallbackFont(font, fallback_font)) {
            SDL_Log("Warning: Failed to add fallback font: %s\\n", SDL_GetError());
        }
    }

    if (!font) {
        SDL_Log("Error: Both fonts failed to load.\\n");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    strcat(confirmed_text, " \\xef\\x8c\\x82"); 

    SDL_StartTextInput(window);

    bool quit = false;
    SDL_Event event;

    while (!quit) {
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) {
                quit = true;
            }
            else if (event.type == SDL_EVENT_TEXT_EDITING) {
                if (event.edit.text) {
                    strncpy(composition_text, event.edit.text, sizeof(composition_text) - 1);
                } else {
                    composition_text[0] = '\\0';
                }
                printf("IME Editing (composition): %s (start: %d, len: %d)\\n", 
                       composition_text, event.edit.start, event.edit.length);
            }
            else if (event.type == SDL_EVENT_TEXT_INPUT) {
                if (event.text.text) {
                    strncat(confirmed_text, event.text.text, sizeof(confirmed_text) - strlen(confirmed_text) - 1);
                }
                composition_text[0] = '\\0';
                printf("IME Input (confirmed): %s\\n", event.text.text);
            }
        }

        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);

        char display_text[2048];
        snprintf(display_text, sizeof(display_text), "%s%s", confirmed_text, composition_text);

        SDL_Color text_color = {255, 255, 255, 255}; 
        float current_x = 20.0f; 
        float current_y = 20.0f; 

        const float ZENKAKU_WIDTH = 24.0f; 

        const char* p = display_text;
        while (*p != '\\0') {
            Uint32 ch = 0;
            int len = 0;

            unsigned char c = (unsigned char)*p;
            if (c < 0x80) { ch = c; len = 1; }
            else if ((c & 0xE0) == 0xC0) { ch = ((c & 0x1F) << 6) | (p[1] & 0x3F); len = 2; }
            else if ((c & 0xF0) == 0xE0) { ch = ((c & 0x0F) << 12) | ((p[1] & 0x3F) << 6) | (p[2] & 0x3F); len = 3; }
            else if ((c & 0xF8) == 0xF0) { ch = ((c & 0x07) << 18) | ((p[1] & 0x3F) << 12) | ((p[2] & 0x3F) << 6) | (p[3] & 0x3F); len = 4; }
            else { len = 1; p++; continue; } 

            bool is_icon = (ch >= 0xE000 && ch <= 0xF8FF);

            SDL_Surface* glyph_surf = TTF_RenderGlyph_Blended(font, ch, text_color);
            if (glyph_surf) {
                SDL_Texture* glyph_tex = SDL_CreateTextureFromSurface(renderer, glyph_surf);
                if (glyph_tex) {
                    float target_w = (float)glyph_surf->w;
                    float target_h = (float)glyph_surf->h;
                    float render_x = current_x;

                    if (is_icon) {
                        float offset_x = (ZENKAKU_WIDTH - target_w) / 2.0f;
                        render_x += offset_x;
                    }

                    SDL_FRect dst_rect = {
                        .x = render_x,
                        .y = current_y,
                        .w = target_w,
                        .h = target_h
                    };

                    SDL_RenderTexture(renderer, glyph_tex, NULL, &dst_rect);
                    SDL_DestroyTexture(glyph_tex);
                }
                SDL_DestroySurface(glyph_surf);
            }

            if (is_icon) {
                current_x += ZENKAKU_WIDTH;
            } else {
                int advance = 0;
                if (TTF_GetGlyphMetrics(font, ch, NULL, NULL, NULL, NULL, &advance)) {
                    current_x += (float)advance;
                } else {
                    current_x += ZENKAKU_WIDTH / 2.0f; 
                }
            }

            p += len; 
        }

        SDL_RenderPresent(renderer);
        SDL_Delay(16);
    }

    SDL_StopTextInput(window);
    if (font) TTF_CloseFont(font);
    if (fallback_font) TTF_CloseFont(fallback_font);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    TTF_Quit();
    SDL_Quit();
    return 0;
}
"""

    with open(os.path.join(project_dir, "CMakeLists.txt"), "w") as f:
        f.write(cmakelists_content)
        
    with open(os.path.join(project_dir, "build.sh"), "w") as f:
        f.write(build_sh_content)
    os.chmod(os.path.join(project_dir, "build.sh"), 0o755)
        
    with open(os.path.join(project_dir, "main.c"), "w") as f:
        f.write(main_c_content)
        
    print(f"Project structure successfully created in directory: {project_dir}")

if __name__ == "__main__":
    main()
