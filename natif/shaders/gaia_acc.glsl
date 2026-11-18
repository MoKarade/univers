/* Inclus par gaia.vert et gaia_agrege.vert. Accélération du potentiel de la Galaxie (bulbe, disque, halo, barre tournante) : COPIE de acc() de orbites_pas.comp
   (fil natif), à garder identique. Unités : kpc, km/s, milliards d'années. */
const float OP_G = 4.30091e-6, OP_MB = 0.5e10, OP_AB = 0.5, OP_MD = 6.8e10, OP_AD = 3.0, OP_BD = 0.28, OP_RS = 16.0;
const float OP_GMH = 2552189.27458262, OP_K = 1.0227121650456, OP_RB = 5.0, OP_ABAR = 796.84938, OP_BAR0 = 2.65290046, OP_BARW = 39.8857744, OP_KL = 0.00311179;  /* OP_KL : énergie noire, phys::galaxie::kLambdaKmsKpc2 */
vec3 accGal(vec3 x, float t) {
    float R2 = x.x * x.x + x.y * x.y, r = sqrt(R2 + x.z * x.z) + 1e-12, xs = r / OP_RS;
    float ar = -OP_G * OP_MB / ((r + OP_AB) * (r + OP_AB)) - OP_GMH * (log(1.0 + xs) - xs / (1.0 + xs)) / (r * r);
    float B = sqrt(x.z * x.z + OP_BD * OP_BD), D2 = R2 + (OP_AD + B) * (OP_AD + B), D3 = D2 * sqrt(D2), gm = OP_G * OP_MD;
    vec3 a = vec3(ar * x.x / r - gm * x.x / D3, ar * x.y / r - gm * x.y / D3, ar * x.z / r - gm * x.z * (OP_AD + B) / (B * D3)) + OP_KL * x;
    if (R2 > 1e-8) {
        /* barre de Dehnen en 3D (Monari et al. 2016) : Φb = A cos2ψ (R/r)² U(r), comme phys::galaxie::Potentiel::acc (revue O1) */
        float R = sqrt(R2), rb = sqrt(R2 + x.z * x.z), c = x.x / R, s = x.y / R, psi = atan(x.y, x.x) - (OP_BAR0 - OP_BARW * t);
        float c2 = cos(2.0 * psi), s2 = sin(2.0 * psi), q = rb / OP_RB;
        float U = rb < OP_RB ? q * q * q - 2.0 : -1.0 / (q * q * q);
        float dU = rb < OP_RB ? 3.0 * q * q / OP_RB : 3.0 / (q * q * q * q * OP_RB);
        float hb = U / (rb * rb), hp = dU / (rb * rb) - 2.0 * U / (rb * rb * rb);
        float G = R2 * hb, dGdR = 2.0 * R * hb + R2 * hp * R / rb, dGdz = R2 * hp * x.z / rb;
        float aR = -OP_ABAR * c2 * dGdR, aP = 2.0 * OP_ABAR * s2 * G / R;
        a.x += aR * c - aP * s;
        a.y += aR * s + aP * c;
        a.z += -OP_ABAR * c2 * dGdz;
    }
    return a;
}
