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
    double yawDeg = 0, pitchDeg = 0;      // contrôle : direction d'où l'on regarde l'astre suivi (longitude et latitude écliptiques, degrés)
    bool hasView = false;
    int skyBand = -1;           // contrôle : rang de la lumière du ciel à montrer (-1 : visible)
    bool checkOrbits = false;   // contrôle : relit les orbites calculées sur la carte et les compare au calcul en double précision
};

int runWindow(const WindowOptions& opt);
