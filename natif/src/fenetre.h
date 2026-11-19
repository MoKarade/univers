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
    double fovDeg = 0;      // --champ : champ de vision de départ (degrés), 0 = 60°
    double yawDeg = 0, pitchDeg = 0;      // contrôle : direction d'où l'on regarde l'astre suivi (longitude et latitude écliptiques, degrés)
    bool hasView = false;
    // contrôle : au lieu de sauter à la date, y aller en laissant défiler le temps depuis pathStart (années depuis J2000) à
    // la vitesse de rang pathRate (kRates), comme le ferait Marc ; l'image finale doit être la même qu'en sautant.
    bool wholeGalaxy = false;   // contrôle : montrer la Galaxie entière du calcul à toute date (Sim::wholeGalaxy)
    bool uncertainty = false;   // contrôle : montrer le nuage des scénarios d'orbite (Sim::showClones, menu « Incertitude »)
    int stopAfter = 0;          // contrôle : s'arrêter après ce nombre de tours de boucle, même si la date n'est pas encore atteinte
    bool hasPath = false;
    double pathStart = 0;
    int pathRate = 0;
    double pathSpeed = 0;       // --vitesse : vitesse libre du trajet (années par seconde), comme le curseur ; 0 : le cran pathRate
    bool realClock = false;     // --horloge-reelle : le trajet suit l'horloge réelle (mesure de la vitesse obtenue et des images/s)
    int skyBand = -1;           // contrôle : rang de la lumière du ciel à montrer (-1 : visible)
    bool checkOrbits = false;   // contrôle : relit les orbites calculées sur la carte et les compare au calcul en double précision
};

int runWindow(const WindowOptions& opt);
