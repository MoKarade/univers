// Appli PC « Univers » : textes du panneau d'information (explications des astres et des grandes époques de l'univers).
//
// Règle du dépôt : chaque chiffre garde sa source et son statut. Les explications ci-dessous ne contiennent que des valeurs
// publiées, avec leur source en fin de texte ; ce qui est approximatif le dit (« environ »). Les valeurs calculées par
// l'appli (âge de l'univers selon les réglages, distances, dates de la rencontre avec Andromède) ne sont pas écrites ici :
// le panneau les calcule et les montre à part, marquées « calculé ».
#pragma once
#include <string>

namespace {

// ---------------------------------------------------------------- astres

struct BodyText {
    const char* name;      // nom exact de l'astre dans l'appli (Body::name)
    const char* image;     // carte de surface dans le dossier textures (Solar System Scope, CC BY 4.0), ou nullptr
    const char* text;
};

const BodyText kBodyTexts[] = {
    {"Soleil", "8k_sun.jpg",
     "Étoile naine jaune, née il y a environ 4,57 milliards d'années. Elle contient 99,86 % de la masse du système solaire. "
     "Dans son cœur, la fusion de l'hydrogène en hélium produit sa lumière. Elle tourne autour du centre de la Voie lactée en "
     "environ 230 millions d'années. Sources : NASA Sun Fact Sheet ; âge : datation des inclusions des météorites (Connelly et al. 2012)."},
    {"Mercure", "8k_mercury.jpg",
     "La plus petite planète et la plus proche du Soleil. Sans atmosphère pour garder la chaleur, sa surface passe d'environ "
     "430 °C le jour à −180 °C la nuit. Un jour solaire y dure deux de ses années. Source : NASA Mercury Fact Sheet."},
    {"Vénus", "4k_venus_atmosphere.jpg",
     "Presque la taille de la Terre, mais une atmosphère de gaz carbonique 92 fois plus lourde : l'effet de serre y maintient "
     "environ 465 °C, la planète la plus chaude. Elle tourne sur elle-même à l'envers, en 243 jours. L'image montre ses nuages. "
     "Source : NASA Venus Fact Sheet."},
    {"Terre", "8k_earth_daymap.jpg",
     "Seule planète connue qui abrite la vie. Formée il y a environ 4,54 milliards d'années ; 71 % de sa surface est couverte "
     "d'océans. Sources : NASA Earth Fact Sheet ; âge : Dalrymple 2001."},
    {"Lune", "8k_moon.jpg",
     "Satellite de la Terre, probablement né d'une collision géante il y a environ 4,5 milliards d'années. Elle s'éloigne de "
     "3,8 cm par an (mesuré par laser sur les réflecteurs d'Apollo). Elle montre toujours la même face à la Terre. "
     "Sources : NASA Moon Fact Sheet ; Williams et Boggs 2016."},
    {"Mars", "8k_mars.jpg",
     "Planète rocheuse, rouge à cause de l'oxyde de fer de son sol. Elle porte le plus haut volcan connu, Olympus Mons, et des "
     "traces d'anciennes rivières. Son atmosphère est 100 fois plus fine que celle de la Terre. Source : NASA Mars Fact Sheet."},
    {"Jupiter", "8k_jupiter.jpg",
     "La plus grande planète : 318 fois la masse de la Terre, surtout de l'hydrogène et de l'hélium. La Grande Tache rouge est "
     "une tempête observée depuis au moins 1830. Elle a 95 lunes reconnues (2023). Source : NASA Jupiter Fact Sheet."},
    {"Saturne", "8k_saturn.jpg",
     "Géante gazeuse aux anneaux de glace, larges de plus de 250 000 km mais épais de quelques dizaines de mètres. "
     "Sa densité moyenne est plus faible que celle de l'eau. Source : NASA Saturn Fact Sheet."},
    {"Uranus", "2k_uranus.jpg",
     "Géante de glace couchée sur le côté : son axe est incliné de 98°, chaque pôle reçoit 42 ans de jour puis 42 ans de nuit. "
     "Source : NASA Uranus Fact Sheet."},
    {"Neptune", "2k_neptune.jpg",
     "Géante de glace la plus lointaine, trouvée en 1846 par le calcul (Le Verrier) avant d'être vue au télescope. Ses vents "
     "dépassent 2 000 km/h. Source : NASA Neptune Fact Sheet."},
    {"Pluton", nullptr,
     "Planète naine de la ceinture de Kuiper, visitée par la sonde New Horizons en 2015, qui y a vu une plaine de glace d'azote "
     "en forme de cœur. Source : NASA Pluto Fact Sheet ; Stern et al. 2015."},
    {"Andromède (M31)", nullptr,
     "La grande galaxie spirale la plus proche, à environ 2,5 millions d'années-lumière. Elle s'approche de la Voie lactée "
     "à environ 110 km/s. Le passage et la fusion des deux galaxies sont calculés dans cette appli : voir la frise. "
     "Sources : McConnachie 2012 ; van der Marel et al. 2012."},
    {"Galaxie du Triangle (M33)", nullptr,
     "Troisième grande galaxie du Groupe local, spirale, à environ 2,7 millions d'années-lumière. Source : McConnachie 2012."},
    {"Grand Nuage de Magellan", nullptr,
     "Galaxie satellite de la Voie lactée, à environ 160 000 années-lumière, visible à l'œil nu depuis l'hémisphère Sud. "
     "Source : Pietrzyński et al. 2019."},
    {"Centre de la Voie lactée", nullptr,
     "Au centre de notre galaxie, à environ 26 700 années-lumière, se trouve Sagittarius A*, un trou noir de 4 millions de masses "
     "solaires dont l'ombre a été photographiée en 2022 (Event Horizon Telescope). Sources : GRAVITY 2019 ; EHT 2022."},
};

// Explication par famille quand l'astre n'a pas de texte propre.
const char* kindText(int kind) {
    switch (kind) {
        case 1: return "Étoile de la Voie lactée. Sa place et sa vitesse viennent des catalogues Hipparcos et Gaia ; loin d'aujourd'hui, "
                       "son chemin est calculé autour du centre de la Galaxie. Voir son orbite ci-dessous.";
        case 2: return "Astre du système solaire. Sa position vient des éphémérides de la NASA (JPL).";
        case 3: return "Galaxie. Sa distance vient des catalogues cités ci-dessous.";
        case 4: return "Sonde spatiale. Sa trajectoire réelle vient du JPL (NASA) : reconstruite pour le passé, prévue pour l'avenir.";
        case 5: return "Petit corps du système solaire. Son orbite vient de la base du JPL (NASA), sans l'attraction des planètes.";
        default: return "";
    }
}

const BodyText* bodyText(const std::string& name) {
    for (const BodyText& t : kBodyTexts)
        if (name == t.name) return &t;
    return nullptr;
}

// ---------------------------------------------------------------- grandes époques (frise)

// Date d'une époque : soit après le Big Bang (fromBigBang), soit par rapport à aujourd'hui. L'âge de l'univers lui-même
// est calculé par l'appli avec les réglages en cours : une époque datée depuis le Big Bang bouge si on change les réglages.
struct Epoch {
    const char* label;      // court, sur la frise
    double years;           // années depuis le Big Bang (fromBigBang) ou depuis aujourd'hui (négatif : passé)
    bool fromBigBang;
    const char* text;       // explication, avec la source
};

const Epoch kEpochs[] = {
    {"Big Bang", 0.0, true,
     "Tout l'univers observable tient dans un volume minuscule, extrêmement chaud et dense, puis se dilate. "
     "L'âge de l'univers vient des mesures du satellite Planck (13,79 milliards d'années, Planck 2018) ; ici il est recalculé "
     "avec tes réglages."},
    {"Premiers noyaux", 3.0 / 525960.0, true,      /* 3 minutes, en années */
     "Entre 3 et 20 minutes environ : les protons et les neutrons s'assemblent en noyaux d'hélium. À la fin, environ un quart "
     "de la masse de la matière ordinaire est de l'hélium. Source : nucléosynthèse primordiale, Particle Data Group (revue BBN)."},
    {"Lumière libérée", 380000.0, true,
     "Vers 380 000 ans, l'univers refroidi à environ 3 000 K devient transparent : la lumière de ce moment nous arrive encore, "
     "c'est le fond diffus cosmologique, mesuré aujourd'hui à 2,7255 K (Fixsen 2009 ; Planck 2018)."},
    {"Premières galaxies", 2.9e8, true,
     "La plus lointaine galaxie confirmée (JADES-GS-z14-0, télescope James Webb) brillait environ 290 millions d'années après "
     "le Big Bang (Carniani et al. 2024). Les toutes premières étoiles sont plus anciennes encore, jamais vues."},
    {"Voie lactée", -1.3e10, false,
     "Les plus vieilles étoiles de notre galaxie ont environ 13 milliards d'années ; le disque où se trouve le Soleil s'est formé "
     "plus tard, peu à peu. [Probable : âges d'étoiles du halo, à quelques centaines de millions d'années près.]"},
    {"Soleil et planètes", -4.567e9, false,
     "Un nuage de gaz s'effondre et forme le Soleil, puis les planètes dans le disque qui l'entoure. Date : les plus vieux grains "
     "des météorites (Connelly et al. 2012)."},
    {"Vie sur Terre", -3.5e9, false,
     "Les plus anciennes traces de vie largement acceptées ont environ 3,5 milliards d'années (stromatolithes). "
     "[Probable : des traces plus anciennes sont discutées.]"},
    {"Fin des dinosaures", -6.6e7, false,
     "Un astéroïde d'environ 10 km frappe le Yucatán (cratère de Chicxulub) : la plupart des dinosaures disparaissent. "
     "Date : 66,0 millions d'années (Renne et al. 2013)."},
    {"Aujourd'hui", 0.0, false,
     "Les étoiles, galaxies, planètes et sondes sont placées d'après les mesures. Hors d'aujourd'hui, leur place est calculée."},
    {"Le Soleil enfle", 5.0e9, false,
     "Dans environ 5 milliards d'années, le Soleil a épuisé l'hydrogène de son cœur et devient une géante rouge, des centaines "
     "de fois plus grande. Bien avant, vers 1 milliard d'années, sa lumière croissante aura fait s'évaporer les océans. "
     "[Probable : Schröder et Smith 2008.]"},
};
constexpr int kEpochCount = static_cast<int>(sizeof(kEpochs) / sizeof(kEpochs[0]));

}  // namespace
