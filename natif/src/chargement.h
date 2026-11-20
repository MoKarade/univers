// Appli PC « Univers » : écran de chargement (demande de Marc, 20/11/2026 : « un écran de chargement »).
//
// Pendant que l'appli lit ses données (catalogues, 98 millions d'étoiles Gaia, film du Groupe local…), une fenêtre plein
// écran montre le nom de l'appli, l'étape en cours, une barre d'avancement et un « Le saviez-vous ? » qui change toutes les
// 7 secondes. La fenêtre vit dans son propre fil d'exécution : elle reste animée même quand le chargement bloque.
// Elle est dessinée par GDI (Windows), sans la carte graphique. La fenêtre principale n'apparaît qu'une fois tout chargé.
//
// L'avancement est celui des étapes franchies (chaque étape annonce sa part), pas une estimation de durée.
// Les faits affichés sont vrais et sourcés ; aucun n'est inventé.
#pragma once
#include <windows.h>

#include <atomic>
#include <cmath>
#include <cstdio>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace chargement {

struct Fait {
    const wchar_t* texte;
    const wchar_t* source;
};
// Faits sûrs, avec leur source (mêmes sources que les fiches de l'appli).
inline const Fait kFaits[] = {
    {L"La lumière du Soleil met environ 8 minutes et 20 secondes pour arriver jusqu'à la Terre.", L"distance moyenne Terre-Soleil, vitesse de la lumière"},
    {L"Le satellite Gaia a mesuré la position d'environ 1,8 milliard de sources de la Voie lactée.", L"Gaia DR3, Agence spatiale européenne, 2022"},
    {L"La lumière d'Andromède que l'on voit ce soir est partie il y a environ 2,5 millions d'années.", L"McConnachie 2012"},
    {L"Le Soleil fait un tour complet de la Voie lactée en environ 230 millions d'années.", L"NASA Sun Fact Sheet"},
    {L"Jupiter comptait 95 lunes reconnues en 2023, plus que toute autre planète à cette date.", L"NASA Jupiter Fact Sheet"},
    {L"L'univers a environ 13,8 milliards d'années.", L"mission Planck, 2018"},
    {L"Voyager 1, lancée en 1977, est l'objet fabriqué le plus lointain : à plus de 160 fois la distance Terre-Soleil.", L"trajectoire JPL Horizons"},
};
constexpr int kFaitsCount = static_cast<int>(sizeof(kFaits) / sizeof(kFaits[0]));

// État partagé entre le chargement (qui écrit) et la fenêtre (qui lit).
struct Etat {
    std::mutex m;
    std::wstring etape = L"Démarrage";
    float part = 0.0f;      // 0 à 1 : part des étapes franchies
};

// ---------------------------------------------------------------- dessin (aussi utilisé hors fenêtre, pour les contrôles)

inline HFONT police(int px, bool gras) {
    return CreateFontW(-px, 0, 0, 0, gras ? FW_SEMIBOLD : FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                       CLEARTYPE_QUALITY, DEFAULT_PITCH, gras ? L"Segoe UI Semibold" : L"Segoe UI");
}

inline void texteCentre(HDC dc, const std::wstring& t, int px, bool gras, COLORREF c, int cx, int y, int largeur) {
    HFONT f = police(px, gras);
    HGDIOBJ old = SelectObject(dc, f);
    SetTextColor(dc, c);
    RECT r{cx - largeur / 2, y, cx + largeur / 2, y + px * 4};
    DrawTextW(dc, t.c_str(), -1, &r, DT_CENTER | DT_WORDBREAK | DT_NOPREFIX);
    SelectObject(dc, old);
    DeleteObject(f);
}

inline void rectArrondi(HDC dc, int x0, int y0, int x1, int y1, int rayon, COLORREF c) {
    HBRUSH b = CreateSolidBrush(c);
    HPEN p = CreatePen(PS_SOLID, 1, c);
    HGDIOBJ ob = SelectObject(dc, b), op = SelectObject(dc, p);
    RoundRect(dc, x0, y0, x1, y1, rayon, rayon);
    SelectObject(dc, ob);
    SelectObject(dc, op);
    DeleteObject(b);
    DeleteObject(p);
}

// Une image de l'écran de chargement. `t` : secondes depuis le début (animation), `part` : avancement 0 à 1.
inline void peindre(HDC dc, int w, int h, const std::wstring& etape, float part, double t) {
    // Fond : dégradé vertical bleu nuit.
    TRIVERTEX v[2] = {{0, 0, 0x0500, 0x0700, 0x0D00, 0xFF00}, {w, h, 0x0B00, 0x1000, 0x2000, 0xFF00}};
    GRADIENT_RECT gr{0, 1};
    GradientFill(dc, v, 2, &gr, 1, GRADIENT_FILL_RECT_V);
    SetBkMode(dc, TRANSPARENT);
    const int cx = w / 2, cy = static_cast<int>(h * 0.33);
    const float s = h / 1080.0f;

    // Motif : orbites concentriques, inclinées comme un système vu de biais (décor, pas des données).
    HGDIOBJ oldBrush = SelectObject(dc, GetStockObject(HOLLOW_BRUSH));
    for (int k = 1; k <= 5; ++k) {
        const int rx = static_cast<int>((150 + k * 95) * s), ry = static_cast<int>(rx * 0.34f);
        const int a = 46 - k * 6;
        HPEN p = CreatePen(PS_SOLID, 1, RGB(a, a + 8, a + 26));
        HGDIOBJ op = SelectObject(dc, p);
        Ellipse(dc, cx - rx, cy - ry, cx + rx, cy + ry);
        // Un point par orbite qui tourne lentement : seulement pour montrer que l'appli travaille.
        const double ang = t * (0.9 / k) + k * 1.7;
        const int px = cx + static_cast<int>(rx * std::cos(ang)), py = cy + static_cast<int>(ry * std::sin(ang));
        const int d = static_cast<int>(std::max(2.0f, 3.5f * s));
        rectArrondi(dc, px - d, py - d, px + d, py + d, 2 * d, k == 3 ? RGB(255, 186, 96) : RGB(150, 160, 185));
        SelectObject(dc, op);
        DeleteObject(p);
    }
    SelectObject(dc, oldBrush);
    // Soleil au centre : disque ambre.
    const int sr = static_cast<int>(14 * s);
    rectArrondi(dc, cx - sr - 6, cy - sr - 6, cx + sr + 6, cy + sr + 6, 2 * sr + 12, RGB(60, 44, 24));
    rectArrondi(dc, cx - sr, cy - sr, cx + sr, cy + sr, 2 * sr, RGB(255, 196, 110));

    // Titre et sous-titre.
    const int yTitle = static_cast<int>(h * 0.56);
    texteCentre(dc, L"Univers", static_cast<int>(64 * s), true, RGB(234, 238, 246), cx, yTitle, w);
    texteCentre(dc, L"Du système solaire à l'horizon cosmique, d'après des mesures réelles", static_cast<int>(20 * s), false, RGB(148, 158, 178), cx,
                yTitle + static_cast<int>(88 * s), w);

    // Barre d'avancement : la part franchie en ambre ; un reflet qui glisse montre que le travail continue.
    const int bw = static_cast<int>(420 * s), bh = std::max(4, static_cast<int>(5 * s));
    const int bx = cx - bw / 2, by = yTitle + static_cast<int>(150 * s);
    rectArrondi(dc, bx, by, bx + bw, by + bh, bh, RGB(34, 40, 58));
    const int fw = static_cast<int>(bw * std::clamp(part, 0.0f, 1.0f));
    if (fw > bh) rectArrondi(dc, bx, by, bx + fw, by + bh, bh, RGB(255, 186, 96));
    if (fw < bw) {
        const double ph = std::fmod(t * 0.6, 1.0);
        const int gx = bx + fw + static_cast<int>((bw - fw) * ph), gw = std::min(static_cast<int>(60 * s), bx + bw - gx);
        if (gw > bh) rectArrondi(dc, gx, by, gx + gw, by + bh, bh, RGB(70, 76, 98));
    }
    texteCentre(dc, etape, static_cast<int>(16 * s), false, RGB(148, 158, 178), cx, by + static_cast<int>(20 * s), w);

    // Le saviez-vous ? : change toutes les 7 secondes.
    const Fait& f = kFaits[static_cast<int>(t / 7.0) % kFaitsCount];
    const int yFact = h - static_cast<int>(170 * s), fw2 = static_cast<int>(820 * s);
    texteCentre(dc, L"LE SAVIEZ-VOUS ?", static_cast<int>(13 * s), true, RGB(255, 186, 96), cx, yFact, w);
    texteCentre(dc, f.texte, static_cast<int>(20 * s), false, RGB(214, 222, 238), cx, yFact + static_cast<int>(26 * s), fw2);
    texteCentre(dc, std::wstring(L"Source : ") + f.source, static_cast<int>(13 * s), false, RGB(98, 108, 130), cx, yFact + static_cast<int>(86 * s), fw2);
}

// Contrôle sans fenêtre : peint une image de l'écran de chargement dans un fichier PPM (aucune carte graphique).
inline bool capture(const char* path, int w, int h, const std::wstring& etape, float part, double t) {
    HDC screen = GetDC(nullptr);
    HDC dc = CreateCompatibleDC(screen);
    BITMAPINFO bi{};
    bi.bmiHeader = {sizeof(BITMAPINFOHEADER), w, -h, 1, 32, BI_RGB, 0, 0, 0, 0, 0};
    void* bits = nullptr;
    HBITMAP bmp = CreateDIBSection(dc, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
    HGDIOBJ old = SelectObject(dc, bmp);
    peindre(dc, w, h, etape, part, t);
    GdiFlush();
    bool ok = false;
    if (FILE* fp = std::fopen(path, "wb")) {
        std::fprintf(fp, "P6\n%d %d\n255\n", w, h);
        const unsigned char* p = static_cast<const unsigned char*>(bits);
        std::vector<unsigned char> line(static_cast<size_t>(w) * 3);
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                const unsigned char* q = p + (static_cast<size_t>(y) * w + x) * 4;
                line[static_cast<size_t>(x) * 3] = q[2];
                line[static_cast<size_t>(x) * 3 + 1] = q[1];
                line[static_cast<size_t>(x) * 3 + 2] = q[0];
            }
            std::fwrite(line.data(), 1, line.size(), fp);
        }
        ok = std::fclose(fp) == 0;
    }
    SelectObject(dc, old);
    DeleteObject(bmp);
    DeleteDC(dc);
    ReleaseDC(nullptr, screen);
    return ok;
}

// ---------------------------------------------------------------- fenêtre, dans son propre fil

class Ecran {
public:
    // Ouvre l'écran plein écran sur le moniteur principal. Rien n'est ouvert en contrôle (`visible` faux).
    void ouvrir(bool visible) {
        if (!visible) return;
        fil_ = std::thread([this] { boucle(); });
    }
    // Étape suivante : son nom et la part du chargement franchie à son début.
    void etape(const wchar_t* nom, float part) {
        std::lock_guard<std::mutex> l(etat_.m);
        etat_.etape = nom;
        etat_.part = std::max(etat_.part, part);
    }
    // Ferme l'écran (la fenêtre principale prend la place).
    void fermer() {
        if (!fil_.joinable()) return;
        fini_ = true;
        if (HWND h = hwnd_.load()) PostMessageW(h, WM_CLOSE, 0, 0);
        fil_.join();
    }
    ~Ecran() { fermer(); }

private:
    Etat etat_;
    std::thread fil_;
    std::atomic<HWND> hwnd_{nullptr};
    std::atomic<bool> fini_{false};
    DWORD debut_ = 0;
    float affichee_ = 0.0f;      // part montrée : rejoint doucement la part franchie

    static LRESULT CALLBACK proc(HWND h, UINT msg, WPARAM wp, LPARAM lp) {
        auto* self = reinterpret_cast<Ecran*>(GetWindowLongPtrW(h, GWLP_USERDATA));
        switch (msg) {
            case WM_TIMER: InvalidateRect(h, nullptr, FALSE); return 0;
            case WM_ERASEBKGND: return 1;
            case WM_PAINT: {
                PAINTSTRUCT ps;
                HDC dc = BeginPaint(h, &ps);
                if (self) self->peindreFenetre(h, dc);
                EndPaint(h, &ps);
                return 0;
            }
            case WM_CLOSE: DestroyWindow(h); return 0;
            case WM_DESTROY: PostQuitMessage(0); return 0;
            default: return DefWindowProcW(h, msg, wp, lp);
        }
    }

    void peindreFenetre(HWND h, HDC dc) {
        RECT rc;
        GetClientRect(h, &rc);
        const int w = rc.right, hh = rc.bottom;
        HDC mem = CreateCompatibleDC(dc);
        HBITMAP bmp = CreateCompatibleBitmap(dc, w, hh);
        HGDIOBJ old = SelectObject(mem, bmp);
        std::wstring etape;
        float part = 0;
        {
            std::lock_guard<std::mutex> l(etat_.m);
            etape = etat_.etape;
            part = etat_.part;
        }
        affichee_ += (part - affichee_) * 0.15f;
        peindre(mem, w, hh, etape, affichee_, (GetTickCount() - debut_) / 1000.0);
        BitBlt(dc, 0, 0, w, hh, mem, 0, 0, SRCCOPY);
        SelectObject(mem, old);
        DeleteObject(bmp);
        DeleteDC(mem);
    }

    void boucle() {
        WNDCLASSW wc{};
        wc.lpfnWndProc = proc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.lpszClassName = L"UniversChargement";
        wc.hCursor = LoadCursorW(nullptr, reinterpret_cast<LPCWSTR>(IDC_APPSTARTING));
        RegisterClassW(&wc);
        MONITORINFO mi{sizeof(mi)};
        GetMonitorInfoW(MonitorFromPoint({0, 0}, MONITOR_DEFAULTTOPRIMARY), &mi);
        const RECT& r = mi.rcMonitor;
        HWND h = CreateWindowExW(WS_EX_APPWINDOW, wc.lpszClassName, L"Univers : chargement", WS_POPUP, r.left, r.top, r.right - r.left, r.bottom - r.top,
                                 nullptr, nullptr, wc.hInstance, nullptr);
        if (!h) return;
        SetWindowLongPtrW(h, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(this));
        debut_ = GetTickCount();
        hwnd_ = h;
        ShowWindow(h, SW_SHOW);
        SetForegroundWindow(h);
        SetTimer(h, 1, 33, nullptr);      // 30 images par seconde
        if (fini_) PostMessageW(h, WM_CLOSE, 0, 0);
        MSG msg;
        while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        hwnd_ = nullptr;
    }
};

}  // namespace chargement
