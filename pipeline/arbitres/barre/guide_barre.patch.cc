#ifdef EXTERNALGRAVITY_GUIDEBAR
      {
        /* Barre « guide » de pipeline/fusion/stabilite_tir.py (guide_barre) : aiguille adoucie de Long & Murali 1992,
           qui tourne autour de +z, centrée sur l'origine. Masse 2e9 M☉, demi-longueur 5 kpc, largeurs 0,6 et 0,35 kpc,
           39 km/s/kpc, montée 0,3 Ga, tenue 0,2 Ga, descente 0,5 Ga (mêmes valeurs que v9/murir.sh). Dérivées par
           différences centrées (h = 1e-3 kpc), comme l'original. Temps : 1 unité = 0,9778 Ga (T_UNIT de l'original). */
        const double tga = All.Time * 0.9778, tm = 0.3, tt = 0.2, td = 0.5;
        double f = 0;
        if(tga < tm)
          f = 0.5 * (1 - cos(M_PI * tga / tm));
        else if(tga < tm + tt)
          f = 1.0;
        else if(tga < tm + tt + td)
          f = 0.5 * (1 + cos(M_PI * (tga - tm - tt) / td));
        if(f > 0)
          {
            vector<double> pos;
            Sp.nearest_image_intpos_to_pos(Sp.P[target].IntPos, intpos_center, pos.da);
            const double a = 5.0, b = 0.6, c = 0.35, gm = All.G * f * 0.2; /* 2e9 M☉ = 0,2 unité */
            const double ang = 39.0 * 1.0227121650456 * tga, co = cos(ang), si = sin(ang);
            const double x = pos[0] * co + pos[1] * si, y = -pos[0] * si + pos[1] * co, z = pos[2], h = 1e-3;
            auto phi = [&](double X, double Y, double Z) {
              const double q = Y * Y + pow(b + sqrt(c * c + Z * Z), 2);
              const double tp = sqrt((a + X) * (a + X) + q), tn = sqrt((a - X) * (a - X) + q);
              return gm / (2 * a) * log((X - a + tn) / (X + a + tp));
            };
            const double ax = -(phi(x + h, y, z) - phi(x - h, y, z)) / (2 * h);
            const double ay = -(phi(x, y + h, z) - phi(x, y - h, z)) / (2 * h);
            const double az = -(phi(x, y, z + h) - phi(x, y, z - h)) / (2 * h);
            Sp.P[target].GravAccel[0] += ax * co - ay * si;
            Sp.P[target].GravAccel[1] += ax * si + ay * co;
            Sp.P[target].GravAccel[2] += az;
          }
      }
#endif
