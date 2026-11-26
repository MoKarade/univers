// Appli PC « Univers » : projection mémoire en lecture seule portable (Win32 / POSIX), RAII.
#pragma once
#include <cstddef>
#include <cstdint>
#include <limits>
#include <string>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace univers {

class MappedFile {
public:
    MappedFile() = default;
    ~MappedFile() { close(); }

    MappedFile(const MappedFile&) = delete;
    MappedFile& operator=(const MappedFile&) = delete;

    MappedFile(MappedFile&& other) noexcept : view_(other.view_), size_(other.size_), valid_(other.valid_) {
        other.view_ = nullptr;
        other.size_ = 0;
        other.valid_ = false;
    }

    MappedFile& operator=(MappedFile&& other) noexcept {
        if (this != &other) {
            close();
            view_ = other.view_;
            size_ = other.size_;
            valid_ = other.valid_;
            other.view_ = nullptr;
            other.size_ = 0;
            other.valid_ = false;
        }
        return *this;
    }

    bool open(const char* path, std::string* error = nullptr) {
        close();
        auto failOpen = [&](const std::string& msg) {
            if (error) *error = msg;
            return false;
        };
        if (!path || !*path) return failOpen("chemin de fichier vide");
#ifdef _WIN32
        HANDLE file =
            CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) return failOpen(std::string("impossible d'ouvrir ") + path);
        LARGE_INTEGER li{};
        if (!GetFileSizeEx(file, &li) || li.QuadPart < 0) {
            CloseHandle(file);
            return failOpen(std::string("taille de fichier invalide : ") + path);
        }
        const uint64_t sz = static_cast<uint64_t>(li.QuadPart);
        if constexpr (sizeof(size_t) < sizeof(uint64_t)) {
            if (sz > std::numeric_limits<size_t>::max()) {
                CloseHandle(file);
                return failOpen(std::string("fichier trop volumineux : ") + path);
            }
        }
        if (sz == 0) {
            CloseHandle(file);
            valid_ = true;
            return true;
        }
        HANDLE mapping = CreateFileMappingA(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
        if (!mapping) {
            CloseHandle(file);
            return failOpen(std::string("projection mémoire impossible : ") + path);
        }
        void* view = MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0);
        CloseHandle(mapping);
        CloseHandle(file);
        if (!view) return failOpen(std::string("projection mémoire impossible : ") + path);
        view_ = view;
        size_ = static_cast<size_t>(sz);
        valid_ = true;
        return true;
#else
        const int fd = ::open(path, O_RDONLY);
        if (fd < 0) return failOpen(std::string("impossible d'ouvrir ") + path);
        struct stat st {};
        if (::fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size < 0) {
            ::close(fd);
            return failOpen(std::string("fichier non régulier ou taille invalide : ") + path);
        }
        const uint64_t sz = static_cast<uint64_t>(st.st_size);
        if constexpr (sizeof(size_t) < sizeof(uint64_t)) {
            if (sz > std::numeric_limits<size_t>::max()) {
                ::close(fd);
                return failOpen(std::string("fichier trop volumineux : ") + path);
            }
        }
        if (sz == 0) {
            ::close(fd);
            valid_ = true;
            return true;
        }
        void* view = ::mmap(nullptr, static_cast<size_t>(sz), PROT_READ, MAP_PRIVATE, fd, 0);
        ::close(fd);
        if (view == MAP_FAILED) return failOpen(std::string("projection mémoire impossible : ") + path);
        view_ = view;
        size_ = static_cast<size_t>(sz);
        valid_ = true;
        return true;
#endif
    }

    bool open(const std::string& path, std::string* error = nullptr) { return open(path.c_str(), error); }

    void close() noexcept {
        if (view_) {
#ifdef _WIN32
            UnmapViewOfFile(view_);
#else
            ::munmap(view_, size_);
#endif
        }
        view_ = nullptr;
        size_ = 0;
        valid_ = false;
    }

    const uint8_t* data() const noexcept { return static_cast<const uint8_t*>(view_); }
    size_t size() const noexcept { return size_; }
    bool valid() const noexcept { return valid_; }

private:
    void* view_ = nullptr;
    size_t size_ = 0;
    bool valid_ = false;
};

}  // namespace univers
