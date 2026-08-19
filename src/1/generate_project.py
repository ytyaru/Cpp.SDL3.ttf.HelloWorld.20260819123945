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
    main_c_content = """#define _GNU_SOURCE
#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#define WINDOW_WIDTH 800
#define WINDOW_HEIGHT 600

// 日本語の確定テキストとIME入力中（未確定）テキストの保持バッファ
char confirmed_text[1024] = "日本語入力テスト: ";
char composition_text[512] = "";

int main(int argc, char* argv[]) {
    // 1. SDL3 と SDL3_ttf の初期化
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        SDL_Log("SDL_Init Error: %s", SDL_GetError());
        return 1;
    }
    if (!TTF_Init()) {
        SDL_Log("TTF_Init Error: %s", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    // 2. ウィンドウとレンダラーの作成
    SDL_Window* window = SDL_CreateWindow("SDL3 IME & Font Fallback Demo", WINDOW_WIDTH, WINDOW_HEIGHT, 0);
    if (!window) {
        SDL_Log("Window Creation Error: %s", SDL_GetError());
        TTF_Quit();
        SDL_Quit();
        return 1;
    }
    SDL_Renderer* renderer = SDL_CreateRenderer(window, NULL);
    if (!renderer) {
        SDL_Log("Renderer Creation Error: %s", SDL_GetError());
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    // 3. フォントのロードとフォールバック設定
    const char* main_font_path = "/home/pi/.fonts/UDEVGothicJPDOC-Regular.ttf";
    const char* fallback_font_path = "/home/pi/.fonts/UDEVGothicNF-Regular.ttf";

    TTF_Font* font = TTF_OpenFont(main_font_path, 24);
    TTF_Font* fallback_font = TTF_OpenFont(fallback_font_path, 24);

    if (!font) {
        SDL_Log("Warning: Failed to load main font. trying fallback directly.");
        font = fallback_font;
        fallback_font = NULL;
    } else if (fallback_font) {
        // SDL3_ttf の正しい仕様: 第一引数、第二引数ともに TTF_Font* を渡す
        if (!TTF_AddFallbackFont(font, fallback_font)) {
            SDL_Log("Warning: Failed to add fallback font: %s", SDL_GetError());
        }
    }

    if (!font) {
        SDL_Log("Error: Both fonts failed to load.");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    // 初期テキストの末尾に、フォールバックのNFアイコン（例として親指アップのNFアイコン UTF-8）をテスト付与
    // メインフォントにこのコードが無ければ、自動的にNFフォントから描画されます
    strcat(confirmed_text, " \xef\x8c\x82"); 

    // 4. IME入力を有効化
    SDL_StartTextInput(window);

    bool quit = false;
    SDL_Event event;

    // メインループ
    while (!quit) {
        // イベント処理
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) {
                quit = true;
            }
            // SDL3のIME入力中イベント
            else if (event.type == SDL_EVENT_TEXT_EDITING) {
                // event.edit.text に未確定文字列が入る
                if (event.edit.text) {
                    strncpy(composition_text, event.edit.text, sizeof(composition_text) - 1);
                } else {
                    composition_text[0] = '\0';
                }
                printf("IME Editing (composition): %s (start: %d, len: %d)\n", 
                       composition_text, event.edit.start, event.edit.length);
            }
            // SDL3のIME確定入力イベント
            else if (event.type == SDL_EVENT_TEXT_INPUT) {
                // 確定した文字を後ろに結合
                if (event.text.text) {
                    strncat(confirmed_text, event.text.text, sizeof(confirmed_text) - strlen(confirmed_text) - 1);
                }
                // 確定したので入力中バッファはクリア
                composition_text[0] = '\0';
                printf("IME Input (confirmed): %s\n", event.text.text);
            }
        }

        // 5. 描画処理
        // 画面を黒でクリア
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 250);
        SDL_RenderClear(renderer);

        // 表示用の一時フルテキストバッファを合成 (確定分 + 入力中分)
        char display_text[2048];
        snprintf(display_text, sizeof(display_text), "%s%s", confirmed_text, composition_text);

        // SDL3_ttfによる文字列のレンダリング (Blendedモードで綺麗に描画)
        SDL_Color text_color = {255, 255, 255, 255}; // 白色
        SDL_Surface* surface = TTF_RenderText_Blended(font, display_text, 0, text_color);
        
        if (surface) {
            // サーフェスからSDL3のテクスチャを作成
            SDL_Texture* texture = SDL_CreateTextureFromSurface(renderer, surface);
            if (texture) {
                // 描画位置の設定
                SDL_FRect dst_rect = {
                    .x = 20.0f,
                    .y = 20.0f,
                    .w = (float)surface->w,
                    .h = (float)surface->h
                };
                // SDL3の正しい描画関数 (旧 SDL_RenderCopy から変更)
                SDL_RenderTexture(renderer, texture, NULL, &dst_rect);
                SDL_DestroyTexture(texture);
            }
            SDL_DestroySurface(surface);
        }

        // 画面の更新
        SDL_RenderPresent(renderer);
        SDL_Delay(16); // 約60FPSを維持
    }

    // 6. クリーンアップ
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
