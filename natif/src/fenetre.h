// Appli PC « Univers » : ce que univers.cpp demande à la fenêtre.
#pragma once
#include <string>

struct WindowOptions {
    std::string starsPath;
    int testFrames = 0;         // > 0 : contrôle, fenêtre cachée, ce nombre d'images puis sortie
    std::string capture;        // contrôle : fichier .ppm où écrire l'image finale, interface comprise
    std::string target;         // nom de l'astre suivi au départ (défaut : le Soleil)
    double dist = 0;            // distance de départ à l'astre suivi, en années-lumière (0 : défaut)
    double years = 0;           // date de départ, en années depuis J2000,0
    bool hasYears = false;
};

int runWindow(const WindowOptions& opt);
