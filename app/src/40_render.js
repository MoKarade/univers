/* ============================================================================
   RENDU — une seule caméra à distance fixe de l'origine ; chaque couche a sa
   propre unité (UA, année-lumière, kpc, Mpc) et est replacée à chaque image
   par rapport à la cible, en double précision, pour couvrir 20 ordres de grandeur.
   ============================================================================ */
const CAM_D = 10, FOV = 40;
const LOG = { AU: Math.log10(AU), LY: Math.log10(LY), KPC: Math.log10(KPC), MPC: Math.log10(MPC) };
const fadeIn = (x, a, b) => smoothstep(a, b, x), fadeOut = (x, a, b) => 1 - smoothstep(a, b, x);

const BODIES = [   // rayon équatorial (km), aplatissement, pôle nord (AD, déc.), rotation W0 + W1·jours (UAI), taille mini à l'écran (px)
  { key: 'sun', name: 'Soleil', r: 695700, f: 0, pole: [286.13, 63.87], w0: 84.176, w1: 14.1844, minPx: 7, focusR: 5.2e9, info: 'Étoile de type G2, 1,39 million de km de diamètre. Elle contient 99,86 % de la masse du système solaire.' },
  { key: 'mercury', name: 'Mercure', r: 2439.7, f: 0, pole: [281.0103, 61.4155], w0: 329.5988, w1: 6.1385108, minPx: 2.6, focusR: 1.1e7, atmo: [0, 0, 0], atmoK: 0, info: '4 879 km de diamètre, un tour du Soleil en 88 jours.' },
  { key: 'venus', name: 'Vénus', r: 6051.8, f: 0, pole: [272.76, 67.16], w0: 160.20, w1: -1.4813688, minPx: 3.4, focusR: 2.6e7, atmo: [1.0, 0.86, 0.6], atmoK: 0.5, info: '12 104 km de diamètre, un tour du Soleil en 225 jours. Elle tourne sur elle-même à l’envers.' },
  { key: 'earth', name: 'Terre', r: 6378.1, f: 0.00335, pole: [0, 90], w0: 190.147, w1: 360.9856235, minPx: 3.6, focusR: 5.6e8, atmo: [0.35, 0.6, 1.0], atmoK: 0.9, info: '12 742 km de diamètre, un tour du Soleil en 365,25 jours.' },
  { key: 'moon', name: 'Lune', r: 1737.4, f: 0, minPx: 2.0, focusR: 8e6, atmo: [0, 0, 0], atmoK: 0, info: '3 475 km de diamètre, à 384 400 km de la Terre en moyenne, un tour en 27,3 jours.' },
  { key: 'mars', name: 'Mars', r: 3396.2, f: 0.00589, pole: [317.681, 52.887], w0: 176.630, w1: 350.89198226, minPx: 3.0, focusR: 1.5e7, atmo: [1.0, 0.6, 0.4], atmoK: 0.25, info: '6 779 km de diamètre, un tour du Soleil en 687 jours.' },
  { key: 'jupiter', name: 'Jupiter', r: 71492, f: 0.06487, pole: [268.057, 64.495], w0: 284.95, w1: 870.536, minPx: 5.4, focusR: 3.4e8, atmo: [1.0, 0.9, 0.75], atmoK: 0.3, info: '139 820 km de diamètre, un tour du Soleil en 11,9 ans.' },
  { key: 'saturn', name: 'Saturne', r: 60268, f: 0.09796, pole: [40.589, 83.537], w0: 38.90, w1: 810.7939024, minPx: 4.8, focusR: 4.2e8, atmo: [1.0, 0.92, 0.7], atmoK: 0.3, ring: [1.1773, 2.3367], info: '116 460 km de diamètre, un tour du Soleil en 29,5 ans. Ses anneaux s’étendent sur 280 000 km.' },
  { key: 'uranus', name: 'Uranus', r: 25559, f: 0.02293, pole: [257.311, -15.175], w0: 203.81, w1: -501.1600928, minPx: 4.0, focusR: 1.3e8, atmo: [0.6, 0.95, 1.0], atmoK: 0.4, info: '50 724 km de diamètre, un tour du Soleil en 84 ans. Elle roule sur son orbite, couchée sur le côté.' },
  { key: 'neptune', name: 'Neptune', r: 24764, f: 0.01708, pole: [299.36, 43.46], w0: 249.978, w1: 541.1397757, minPx: 4.0, focusR: 1.3e8, atmo: [0.4, 0.55, 1.0], atmoK: 0.5, info: '49 244 km de diamètre, un tour du Soleil en 165 ans.' },
];
const BODY = Object.fromEntries(BODIES.map(b => [b.key, b]));
const ORBIT_KEYS = ['mercury', 'venus', 'emb', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];

/* ------------------------------------------------------------------ shaders */
const GLSL_NOISE = `
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x,289.0);} vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){ const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx); vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy; i=mod(i,289.0);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=1.0/7.0; vec3 ns=n_*D.wyz-D.xzx; vec4 j=p-49.0*floor(p*ns.z*ns.z); vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y); vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0)); vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3))); p0*=norm.x; p1*=norm.y; p2*=norm.z; p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m; return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3))); }`;

const FRAG_SOFT = `varying vec3 vColor; varying float vA;
void main(){ vec2 p=gl_PointCoord*2.0-1.0; float d2=dot(p,p); if(d2>1.0) discard; gl_FragColor=vec4(vColor*vA*(exp(-d2*4.2)-0.015),1.0); }`;

const SH = {
  star: { v: `attribute float aMag; attribute vec3 aCol; attribute vec3 aLife; attribute float aFate; attribute vec3 aVel; uniform float uUnitToPc,uExpo,uOpacity,uDpr,uEvolve,uT,uFlash,uVt,uMcut,uTgtR; uniform vec3 uTgt; varying vec3 vColor; varying float vA; varying float vCore;
void main(){ vec4 mv=modelViewMatrix*vec4(position+aVel*uVt,1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0;
  float M=aMag; vec3 col=aCol; float vis=1.0;
  if(uEvolve>0.5){   // vie de l'étoile : naine, puis géante, puis naine blanche ou supernova
    float tB=aLife.x,tM=aLife.y,tD=aLife.z; float gNow=step(1.5,aFate)*(1.0-step(3.5,aFate)); float sn=step(0.5,aFate)*(1.0-step(1.5,aFate))+step(2.5,aFate)*(1.0-step(3.5,aFate));
    float x0=clamp(-tB/max(tM-tB,1e-3),0.0,1.0);
    if(aFate>3.5){ M=aMag+2.5*log((1.0+max(uT-tD,0.0)/200.0)/(1.0+max(-tD,0.0)/200.0))/2.302585; if(uT<tD){ M=aMag-8.0; col=vec3(1.0,0.6,0.35); } if(uT<tM) vis=0.0; }
    else if(uT<tB) vis=0.0;
    else if(uT<tM){ float x=(uT-tB)/max(tM-tB,1e-3); if(gNow>0.5){ M=aMag+3.0+1.5*(1.0-x); col=mix(vec3(0.85,0.9,1.0),aCol,0.3); } else M=aMag-0.7*(x-x0); }
    else if(uT<tD){ float g=(uT-tM)/max(tD-tM,1e-3);
      if(gNow>0.5){ float g0=clamp(-tM/max(tD-tM,1e-3),0.0,1.0); M=g<g0?aMag+3.0*(1.0-g/max(g0,1e-3)):aMag-1.2*(g-g0); }
      else { M=mix(aMag-0.7*(1.0-x0),aMag-(sn>0.5?2.0:4.5),g); col=mix(aCol,vec3(1.0,0.55,0.3),smoothstep(0.0,0.5,g)); } }
    else { float dt=uT-tD; if(sn>0.5){ if(dt<uFlash){ M=-17.0+6.0*dt/uFlash; col=vec3(0.85,0.92,1.0); } else vis=0.0; } else { M=11.0+2.5*log(1.0+dt/200.0)/2.302585; col=vec3(0.8,0.88,1.0); } }
  }
  float dpc=max(length(mv.xyz)*uUnitToPc,1e-7); float m=M+5.0*log(dpc/10.0)/2.302585-uExpo; float f=pow(10.0,-0.4*(m-6.5));
  float r=min(0.8+0.62*pow(f,0.27),8.5); vA=clamp(pow(f,0.66)*0.6,0.0,1.0)*uOpacity*vis*(1.0-smoothstep(uMcut-0.8,uMcut,m))*step(uTgtR,distance(position+aVel*uVt,uTgt)); vCore=clamp(f/60.0,0.0,1.0); vColor=col; /* couleur du corps noir telle quelle (S1) : plus de saturation gonflée */ gl_PointSize=r*4.0*uDpr; }`,
    f: `varying vec3 vColor; varying float vA; varying float vCore;
void main(){ vec2 p=gl_PointCoord*2.0-1.0; float d2=dot(p,p); if(d2>1.0) discard; float core=exp(-d2*15.0); float halo=exp(-d2*3.5)*0.16-0.005; vec2 q=abs(p); float spike=(exp(-q.y*26.0)*exp(-q.x*3.2)+exp(-q.x*26.0)*exp(-q.y*3.2))*0.22*vCore*vCore*(1.0-d2);
  gl_FragColor=vec4(mix(vColor,vec3(1.0),core*0.28)*vA*(core*(1.0+3.0*vCore)+max(halo,0.0)*(0.5+vCore)+spike),1.0); }` },
  galaxy: { v: `attribute vec2 aOm; attribute vec3 aCol; attribute vec2 aLook; attribute vec3 aCen; attribute float aGrp; attribute float aId; uniform vec3 uSh[104]; uniform vec3 uAx[104]; uniform vec3 uShift,uShift2,uHide; uniform float uG2,uHideK; uniform float uT1,uT2,uPx,uOpacity,uMinPx,uMaxPx,uFloor,uBigPx,uExag,uStarCap,uInside; varying vec3 vColor; varying float vA;
void main(){ float ang=-(aOm.x*uT1+aOm.y*uT2); float c=cos(ang),s=sin(ang); vec3 ax=uAx[int(aId+0.5)]; vec3 p; if(dot(ax,ax)>0.5){ vec3 d=position-aCen; p=aCen+d*c+cross(ax,d)*s+ax*dot(ax,d)*(1.0-c); } else { p=vec3(c*position.x-s*position.y,s*position.x+c*position.y,position.z); } p=aCen+(p-aCen)*uExag+step(0.5,aGrp)*step(aGrp,1.5)*uShift+step(1.5,aGrp)*uShift2+uSh[int(aId+0.5)];
  vec4 mv=modelViewMatrix*vec4(p,1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0; float sc=length(modelViewMatrix[0].xyz);
  float px=aLook.x*uExag*sc*uPx/max(-mv.z,1e-9); float e=min(1.0,(px*px)/(uMinPx*uMinPx)); float gt=step(0.3,aLook.x); float big=mix(1.0,1.0-smoothstep(uBigPx*0.4,uBigPx*0.95,px),gt); float cap=max(mix(uStarCap*(0.7+aLook.x*8.0),uMaxPx,gt),uMinPx);
  vA=aLook.y*uOpacity*max(e,uFloor)*big*mix(pow(min(1.0,cap/max(px,1e-6)),1.2),1.0,gt); vColor=mix(aCol,vec3(0.95,0.92,0.86)*dot(aCol,vec3(0.3333)),uInside); gl_PointSize=clamp(px,uMinPx,cap)*2.0; vA*=mix(1.0,uG2,step(1.5,aGrp)); vA*=1.0-uHideK*(1.0-step(0.5,distance(aCen,uHide))); }`, f: FRAG_SOFT },
  web: { v: `attribute vec3 aPsi; attribute vec3 aEig; attribute vec4 aRnd; uniform float uD,uPx,uOpacity,uHorizon,uAge,uMinPx,uMaxPx,uSw,uSf,uRW,uCR; varying vec3 vColor; varying float vA; varying vec3 vShape;
float Sof(float r){ return uSw*(1.0-smoothstep(0.6*uRW,uRW,r))+uSf; }
void main(){ vec3 p=position+uD*aPsi; vec3 j=abs(vec3(1.0)+uD*aEig); float dens=1.0/max(j.x*j.y*j.z,0.012); float r=length(position);
  vec4 mv=modelViewMatrix*vec4(p,1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0; float sc=length(modelViewMatrix[0].xyz);
  float px=0.03*(0.6+aRnd.w)*sc*uPx/max(-mv.z,1e-9); float pxc=clamp(px,uMinPx,uMaxPx);
  float pk=(1.0-smoothstep(0.6*uRW,uRW,r))*min(1.0,Sof(uCR)/Sof(r)*(r*r)/(uCR*uCR)); float lod=clamp((pk-aRnd.z)/(0.25*pk+1e-5),0.0,1.0); float b=clamp(0.16+0.52*log(1.0+dens),0.0,2.7);
  float hz=1.0-smoothstep(0.96*uHorizon,uHorizon,r); float born=smoothstep(0.15,0.9,uAge);
  vA=uOpacity*lod*b*aRnd.w*hz*born*min(1.0,0.8+px/uMinPx)*(1.0-smoothstep(uMaxPx*0.5,uMaxPx,px));
  vColor=mix(vec3(0.5,0.68,1.0),vec3(1.0,0.82,0.58),smoothstep(1.5,14.0,dens))*mix(vec3(0.7,0.85,1.25),vec3(1.0),smoothstep(0.5,6.0,uAge));
  vShape=vec3(aRnd.x,aRnd.y,smoothstep(2.0,6.0,pxc)); gl_PointSize=pxc*2.0; }`,
    f: `varying vec3 vColor; varying float vA; varying vec3 vShape;
void main(){ vec2 p=gl_PointCoord*2.0-1.0; float ca=cos(vShape.x),sa=sin(vShape.x); vec2 q=vec2(ca*p.x+sa*p.y,-sa*p.x+ca*p.y); q.y/=mix(1.0,vShape.y,vShape.z);
  float d2=dot(q,q); if(d2>1.0) discard; gl_FragColor=vec4(vColor*vA*(exp(-d2*5.0)-0.0067),1.0); }` },
  far: { v: `attribute vec2 aRnd; uniform float uPx,uOpacity,uHorizon,uAge,uMinPx,uSw,uSf,uRW,uCR; varying vec3 vColor; varying float vA;
float Sof(float r){ return uSw*(1.0-smoothstep(0.6*uRW,uRW,r))+uSf; }
void main(){ float r=length(position); vec4 mv=modelViewMatrix*vec4(position,1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0;
  float pk=min(1.0,Sof(uCR)/Sof(r)*(r*r)/(uCR*uCR)); float lod=clamp((pk-aRnd.x)/(0.25*pk+1e-5),0.0,1.0); float hz=1.0-smoothstep(0.97*uHorizon,uHorizon,r);
  vA=uOpacity*lod*hz*(0.5+0.5*aRnd.y)*smoothstep(0.15,0.9,uAge); vColor=mix(vec3(0.62,0.74,1.0),vec3(1.0,0.86,0.66),fract(aRnd.x*7.31)); gl_PointSize=uMinPx*(2.1+1.3*aRnd.y); }`, f: FRAG_SOFT },
  surv: { v: `attribute float aDist; attribute vec3 aInfo; uniform float uPx,uOpacity,uMinPx,uCR,uHorizon,uAge,uKeep; varying vec3 vColor; varying float vA;
uniform vec3 uZG[64]; uniform vec3 uZQ[64]; uniform vec2 uZM;
vec3 zcol(float z,float q){ float u=clamp(log(1.0+z)/mix(uZM.x,uZM.y,q),0.0,1.0)*63.0; int i=int(min(floor(u),62.0)); float f=u-float(i); return q>0.5?mix(uZQ[i],uZQ[i+1],f):mix(uZG[i],uZG[i+1],f); }
void main(){ float r=aDist; vec4 mv=modelViewMatrix*vec4(position*r,1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0;
  float pk=uKeep*min(1.0,pow(r/uCR,1.7)); float lod=clamp((pk-aInfo.y)/(0.3*pk+1e-5),0.0,1.0);
  float hz=1.0-smoothstep(0.97*uHorizon,uHorizon,r); float q=step(1.5,aInfo.z); float ns=1.0-step(0.5,aInfo.z);
  vColor=zcol(aInfo.x,q);      /* S3 : couleur observée calculée selon z (spectre au repos décalé, œil CIE 1931), table DATA.ZCOL */
  vA=uOpacity*lod*hz*smoothstep(0.15,0.9,uAge)*(0.9+0.3*ns); gl_PointSize=uMinPx*(2.5+1.0*ns+0.6*q); if(vA<=0.002) gl_Position=vec4(2.0,2.0,2.0,1.0); }`, f: FRAG_SOFT },
  dots: { v: `attribute vec2 aLook; uniform float uOpacity,uDpr,uZ; uniform vec3 uColor; varying vec3 vColor; varying float vA;
void main(){ vec4 mv=modelViewMatrix*vec4(position,1.0); gl_Position=projectionMatrix*mv; if(uZ>0.5) gl_Position.z=0.0; vA=aLook.y*uOpacity; vColor=uColor; gl_PointSize=clamp(aLook.x*1.5,1.0,4.5)*uDpr; }`, f: FRAG_SOFT },
  orbit: { v: `attribute float aU; attribute float aSide; uniform vec3 uP,uQ; uniform float uE0,uWidth; uniform vec2 uViewport; varying float vU; varying float vSide;
vec3 rel(float dE){ float sh=sin(0.5*dE); return uP*(-2.0*sin(uE0+0.5*dE)*sh)+uQ*(2.0*cos(uE0+0.5*dE)*sh); }
void main(){ float dE=-aU*6.2831853; vec4 c0=projectionMatrix*modelViewMatrix*vec4(rel(dE),1.0); vec4 c1=projectionMatrix*modelViewMatrix*vec4(rel(dE-0.012),1.0);
  vec2 d=(c1.xy*c0.w-c0.xy*c1.w)*uViewport; float l=length(d); d=l>1e-20?d/l:vec2(1.0,0.0); vec2 n=vec2(-d.y,d.x);
  c0.xy+=n*aSide*uWidth*2.0/uViewport*c0.w; gl_Position=c0; vU=aU; vSide=aSide; }`,
    f: `uniform vec3 uColor; uniform float uOpacity; varying float vU; varying float vSide;
void main(){ float e=1.0-smoothstep(0.35,1.0,abs(vSide)); float trail=mix(1.0,0.16,pow(vU,0.55)); gl_FragColor=vec4(uColor*uOpacity*e*trail,1.0); }` },
  ring: { v: `uniform float uRad; varying vec2 vUv;
void main(){ vec4 c=modelViewMatrix*vec4(0.0,0.0,0.0,1.0); c.xy+=position.xy*uRad*1.08; gl_Position=projectionMatrix*c; gl_Position.z=0.0; vUv=position.xy*1.08; }`,
    f: `uniform vec3 uColor; uniform float uOpacity,uWidth,uDash; varying vec2 vUv;
void main(){ float r=length(vUv); float a=1.0-smoothstep(uWidth*0.5,uWidth*1.6,abs(r-1.0)); if(uDash>0.5) a*=smoothstep(0.42,0.5,abs(fract(atan(vUv.y,vUv.x)/6.2831853*uDash)-0.5)*2.0+0.0);
  if(a<0.003) discard; gl_FragColor=vec4(uColor*uOpacity*a,1.0); }` },
  halo: { f: `uniform vec3 uColor; uniform float uOpacity; varying vec2 vUv;
void main(){ float r=length(vUv); if(r>1.0) discard; gl_FragColor=vec4(uColor*uOpacity*(1.0-r)*(1.0-r)/(0.25+9.0*r),1.0); }` },
  glow: { v: `uniform float uRad; varying vec2 vUv;
void main(){ vec4 c=modelViewMatrix*vec4(0.0,0.0,0.0,1.0); c.xy+=position.xy*uRad; gl_Position=projectionMatrix*c; vUv=position.xy; }`,
    f: `uniform vec3 uColor; uniform float uOpacity,uCore; varying vec2 vUv;
void main(){ float r=length(vUv); if(r>1.0) discard; float g=exp(-r*r*uCore)*1.2+0.09/(0.02+r*r*6.0)*(1.0-r)*(1.0-r); gl_FragColor=vec4(uColor*uOpacity*g,1.0); }` },
  body: { v: `varying vec3 vN; varying vec2 vUv; varying vec3 vW; varying vec3 vO;
void main(){ vUv=uv; vO=position; vN=normalize(mat3(modelMatrix)*normal); vec4 w=modelMatrix*vec4(position,1.0); vW=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }`,
    f: `uniform sampler2D uMap; uniform vec3 uSun,uAtmo; uniform float uAtmoK,uSpin,uGain,uOcean; varying vec3 vN; varying vec2 vUv; varying vec3 vW;
void main(){ vec3 base=texture2D(uMap,vUv).rgb;
  if(uSpin>0.01){ vec3 acc=vec3(0.0); for(int i=0;i<8;i++) acc+=texture2D(uMap,vec2(vUv.x+float(i)/8.0,vUv.y)).rgb; base=mix(base,acc/8.0,uSpin); }
  vec3 N=normalize(vN); float ndl=dot(N,uSun); float day=smoothstep(-0.07,0.2,ndl)*(0.2+0.8*clamp(ndl,0.0,1.0));
  vec3 V=normalize(cameraPosition-vW); float fr=pow(1.0-clamp(dot(N,V),0.0,1.0),3.0);
  float oc=uOcean*smoothstep(0.02,0.12,base.b-max(base.r,base.g)); float sp=pow(max(dot(N,normalize(uSun+V)),0.0),70.0)*oc*step(0.0,ndl);      // reflet du Soleil sur les océans
  gl_FragColor=vec4(base*(day*uGain+0.01)+vec3(1.0,0.94,0.82)*sp*0.85+uAtmo*uAtmoK*fr*smoothstep(-0.15,0.35,ndl),1.0); }` },
  sun: { v: `varying vec3 vN; varying vec3 vW; varying vec3 vO;
void main(){ vO=position; vN=normalize(mat3(modelMatrix)*normal); vec4 w=modelMatrix*vec4(position,1.0); vW=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }`,
    f: GLSL_NOISE + `uniform float uGain,uTime,uDet; uniform vec3 uColor; varying vec3 vN; varying vec3 vW; varying vec3 vO;
void main(){ vec3 V=normalize(cameraPosition-vW); float mu=clamp(dot(normalize(vN),V),0.0,1.0); float limb=1.0-0.6*(1.0-mu);
  float gran=0.93+(0.05*snoise(vO*22.0+uTime*0.07)+0.035*snoise(vO*64.0-uTime*0.11))*uDet; gl_FragColor=vec4(uColor*limb*gran*uGain,1.0); }` },
  satring: { v: `varying vec3 vL; varying vec3 vW;
void main(){ vL=position; vec4 w=modelMatrix*vec4(position,1.0); vW=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }`,
    f: `uniform sampler2D uMap; uniform vec3 uSun,uCenter,uNormal; uniform float uPlanetR,uInner,uOuter,uGain; varying vec3 vL; varying vec3 vW;
void main(){ float t=(length(vL.xy)-uInner)/(uOuter-uInner); if(t<0.0||t>1.0) discard; vec4 tx=texture2D(uMap,vec2(t,0.5));
  vec3 rel=vW-uCenter; float al=dot(rel,uSun); float sh=(al<0.0&&length(rel-uSun*al)<uPlanetR)?0.05:1.0; float l=0.35+0.65*abs(dot(uNormal,uSun));
  gl_FragColor=vec4(tx.rgb*l*sh*uGain*tx.a,tx.a); }` },
  cmb: { v: `varying vec2 vUv; varying vec3 vN; varying vec3 vW;
void main(){ vUv=uv; vN=normalize(mat3(modelMatrix)*normal); vec4 w=modelMatrix*vec4(position,1.0); vW=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; gl_Position.z=0.0; }`,
    f: `uniform sampler2D uMap; uniform float uOpacity; varying vec2 vUv; varying vec3 vN; varying vec3 vW;
vec3 ramp(float t){ t=clamp(t,0.0,1.0); vec3 a=vec3(0.02,0.12,0.5),b=vec3(0.25,0.62,0.95),c=vec3(1.0,0.94,0.78),d=vec3(0.98,0.52,0.12),e=vec3(0.55,0.08,0.04);
  return t<0.25?mix(a,b,t*4.0):t<0.5?mix(b,c,(t-0.25)*4.0):t<0.75?mix(c,d,(t-0.5)*4.0):mix(d,e,(t-0.75)*4.0); }
void main(){ float f=texture2D(uMap,vUv).r; vec3 V=normalize(cameraPosition-vW); float rim=pow(1.0-abs(dot(normalize(vN),V)),1.6);
  gl_FragColor=vec4(ramp(0.5+(f-0.5)*1.7)*uOpacity*(0.05+0.34*rim),1.0); }` },
  fsv: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.0,1.0); }`,
  bright: `uniform sampler2D tMap; uniform vec2 uTexel; uniform float uThresh; varying vec2 vUv;
void main(){ vec3 c=0.25*(texture2D(tMap,vUv+uTexel*vec2(-1.0,-1.0)).rgb+texture2D(tMap,vUv+uTexel*vec2(1.0,-1.0)).rgb+texture2D(tMap,vUv+uTexel*vec2(-1.0,1.0)).rgb+texture2D(tMap,vUv+uTexel*vec2(1.0,1.0)).rgb);
  c=min(c,vec3(24.0)); float l=max(c.r,max(c.g,c.b)); gl_FragColor=vec4(c*smoothstep(uThresh*0.6,uThresh*1.6,l),1.0); }`,
  blur: `uniform sampler2D tMap; uniform vec2 uDir; varying vec2 vUv;
void main(){ vec3 c=texture2D(tMap,vUv).rgb*0.2270270; c+=(texture2D(tMap,vUv+uDir*1.3846154).rgb+texture2D(tMap,vUv-uDir*1.3846154).rgb)*0.3162162;
  c+=(texture2D(tMap,vUv+uDir*3.2307692).rgb+texture2D(tMap,vUv-uDir*3.2307692).rgb)*0.0702703; gl_FragColor=vec4(c,1.0); }`,
  final: `uniform sampler2D tMap,tB1,tB2; uniform float uBloom,uExposure,uTime; uniform vec2 uRes; varying vec2 vUv;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
float hash(vec2 p){ return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453); }
uniform float uLens,uFlip,uPsiC,uCubeOn; uniform samplerCube tCube; uniform sampler2D tLut; uniform vec3 uBH; uniform vec2 uTanF,uLl; uniform mat3 uRot;
float lutAt(float i){ return texture2D(tLut,vec2((i+0.5)/512.0,0.5)).r; }
vec3 lensed(){ if(uLens>1.5) return vec3(0.0);      /* trop près : hors du domaine du calcul, rien n'est montré */
  vec3 v=normalize(vec3((vUv*2.0-1.0)*uTanF,-1.0)); float cp=dot(v,uBH), sp=length(cross(v,uBH)), psi=atan(sp,cp); if(psi<=uPsiC) return vec3(0.0);      /* S6 : l'ombre */
  float x=clamp((log(psi-uPsiC)-uLl.x)/(uLl.y-uLl.x),0.0,1.0)*511.0, i0=min(floor(x),510.0), dp=(3.14159265-psi)+mix(lutAt(i0),lutAt(i0+1.0),x-i0);      /* rayon suivi à rebours (27_lens.js, même calcul que lensSource) */
  vec3 t=(v-cp*uBH)/max(sp,1e-12), s=-cos(dp)*uBH+sin(dp)*t;
  if(s.z<-1e-4){ vec2 q=(s.xy/(-s.z))/uTanF*0.5+0.5; if(uCubeOn<0.5||(q.x>0.0&&q.x<1.0&&q.y>0.0&&q.y<1.0)){ q=clamp(q,0.0,1.0); return texture2D(tMap,q).rgb+uBloom*(texture2D(tB1,q).rgb*0.55+texture2D(tB2,q).rgb*0.75); } }      /* source dans l'image : l'image elle-même, nette */
  if(uCubeOn<0.5) return vec3(0.0);
  vec3 w=uRot*s; return textureCube(tCube,vec3(uFlip*w.x,w.y,w.z)).rgb; }      /* source hors de l'image : vue tout autour, moins fine */
void main(){ vec3 c=uLens>0.5?lensed():texture2D(tMap,vUv).rgb+uBloom*(texture2D(tB1,vUv).rgb*0.55+texture2D(tB2,vUv).rgb*0.75);
  c=aces(c*uExposure); c*=1.0-0.42*smoothstep(0.35,0.95,length(vUv-0.5)*1.25);
  c=pow(c,vec3(1.0/2.2)); c+=(hash(gl_FragCoord.xy+fract(uTime)*91.7)-0.5)/255.0; gl_FragColor=vec4(c,1.0); }`,
};

/* ------------------------------------------------------------------ moteur */
/* ============================================================================
   L'infiniment petit : de la surface de la Terre à 10⁻²⁰ m (au-delà : inconnu, rien n'est dessiné).
   Le point visé est l'origine de la scène. Chaque objet est défini en mètres autour de ce point
   (un quark d'un proton du noyau d'oxygène d'une molécule d'eau), puis multiplié par l'échelle vraie F.sT.
   Le décor astronomique reste figé derrière un fond opaque.
   Mesuré : géométrie de la molécule d'eau, rayon de Bohr, rayons du noyau et du proton, limite de taille des quarks.
   Modèle : position des molécules voisines, détail du nuage d'électrons, arrangement des nucléons, intérieur du proton.
   ============================================================================ */
function initMicro(THREE, scene, camera, R, Q) {
  const ANG = 1e-10, FM = 1e-15, A0 = 0.529177210544, RP = 0.84075, rng = makeRng(4242), big = (Q.oort || 0) >= 10000;
  const M = { pos: {}, k: 0 }, m4 = new THREE.Matrix4(), ORD = 5000, all = [];
  const vis = (lr, lo, hi, w) => fadeIn(lr, lo - (w || 0.35), lo) * fadeOut(lr, hi, hi + (w || 0.35));
  const gam = (k, s) => { let p = 1; for (let i = 0; i < k; i++) p *= 1 - rng(); return -s * Math.log(p); };
  const add = (o, ord) => { o.renderOrder = ORD + ord; o.frustumCulled = false; o.visible = false; scene.add(o); all.push(o); return o; };
  const V3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);

  // fond opaque : il cache le décor astronomique et remet la profondeur à zéro pour les objets minuscules
  const backMat = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide, transparent: true, depthTest: false, depthWrite: false, opacity: 0 });
  const back = add(new THREE.Mesh(new THREE.SphereGeometry(3000, 20, 10), backMat), 0); back.onBeforeRender = r => { r.clearDepth(); };
  const BACK = [[3.3, [0.035, 0.17, 0.27]], [-3.4, [0.035, 0.17, 0.27]], [-4.4, [0.02, 0.10, 0.19]], [-7.5, [0.012, 0.06, 0.13]], [-9, [0.004, 0.012, 0.028]], [-12, [0.002, 0.004, 0.010]], [-36, [0.002, 0.003, 0.007]]];
  const backCol = lr => { for (let i = 0; i < BACK.length - 1; i++) if (lr >= BACK[i + 1][0]) { const a = BACK[i], b = BACK[i + 1], k = clamp((a[0] - lr) / (a[0] - b[0]), 0, 1); return [lerp(a[1][0], b[1][0], k), lerp(a[1][1], b[1][1], k), lerp(a[1][2], b[1][2], k)]; } return BACK[BACK.length - 1][1]; };

  // boules ombrées sans lumière dans la scène : un dégradé peint sert d'éclairage
  const mc = document.createElement('canvas'); mc.width = mc.height = 128;
  { const g = mc.getContext('2d'), gr = g.createRadialGradient(48, 44, 3, 64, 64, 66); gr.addColorStop(0, '#ffffff'); gr.addColorStop(0.3, '#d2d2d2'); gr.addColorStop(0.75, '#707070'); gr.addColorStop(1, '#2c2c2c'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); }
  const matcap = new THREE.CanvasTexture(mc); if (THREE.SRGBColorSpace && 'colorSpace' in matcap) matcap.colorSpace = THREE.SRGBColorSpace;
  const ballMat = col => new THREE.MeshMatcapMaterial({ matcap, color: col, transparent: true, opacity: 1 });
  const sph = new THREE.SphereGeometry(1, 20, 14), sphHi = new THREE.SphereGeometry(1, 44, 30);
  const ptMat = (col, px, kind) => new THREE.ShaderMaterial({ uniforms: { uCol: { value: new THREE.Color(col[0], col[1], col[2]) }, uOp: { value: 0 }, uPx: { value: px }, uT: { value: 0 } }, transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
    vertexShader: (kind === 'c' ? 'attribute vec3 aC; varying vec3 vC;' : '') + 'attribute float aPh; uniform float uPx; uniform float uT; varying float vA; void main(){ gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_PointSize = uPx; ' + (kind === 'c' ? 'vC = aC; vA = aPh;' : kind === 'a' ? 'vA = aPh;' : 'vA = 0.35 + 0.65 * (0.5 + 0.5 * sin(uT * (1.0 + aPh * 4.0) + aPh * 50.0));') + ' }',
    fragmentShader: (kind === 'c' ? 'varying vec3 vC;' : '') + 'uniform vec3 uCol; uniform float uOp; varying float vA; void main(){ vec2 d = gl_PointCoord - 0.5; float r = dot(d, d) * 4.0; if (r > 1.0) discard; float f = (1.0 - r); gl_FragColor = vec4(' + (kind === 'c' ? 'vC' : 'uCol') + ' * f * f * vA * uOp, 1.0); }' });
  const mkPts = (pos, ph, mat, ord, col) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('aPh', new THREE.BufferAttribute(ph, 1)); if (col) g.setAttribute('aC', new THREE.BufferAttribute(col, 3)); return add(new THREE.Points(g, mat), ord); };

  // --- gouttelette d'eau (2 mm de diamètre)
  const dropU = { uOp: { value: 0 } };
  const drop = add(new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32), new THREE.ShaderMaterial({ uniforms: dropU, transparent: true, depthWrite: false,
    vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }',
    fragmentShader: 'uniform float uOp; varying vec3 vN; varying vec3 vV; void main(){ vec3 n = normalize(vN); float f = pow(1.0 - max(dot(n, normalize(vV)), 0.0), 2.2); vec3 c = mix(vec3(0.07, 0.26, 0.38), vec3(0.7, 0.88, 1.0), f); float hl = pow(max(dot(n, normalize(vec3(-0.45, 0.6, 0.66))), 0.0), 70.0); gl_FragColor = vec4(c + hl * 1.4, (0.45 + 0.5 * f + hl) * uOp); }' })), 10);

  // --- molécules d'eau : réseau cubique agité à la densité de l'eau liquide (33,4 molécules par nm³), orientations au hasard
  const SP = 3.105, RM = big ? 14.2 : 11.2, mol = [];
  { const n = Math.ceil(RM / SP); for (let i = -n; i <= n; i++) for (let j = -n; j <= n; j++) for (let k = -n; k <= n; k++) { const c0 = !i && !j && !k, x = i * SP + (c0 ? 0 : rng.range(-0.55, 0.55)), y = j * SP + (c0 ? 0 : rng.range(-0.55, 0.55)), z = k * SP + (c0 ? 0 : rng.range(-0.55, 0.55)), d = Math.hypot(x, y, z); if (d > RM) continue;
      const q = c0 ? new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2) : new THREE.Quaternion().setFromAxisAngle(V3(rng.dir()), rng() * TAU);
      mol.push({ c: [x, y, z], d, q, ph: [rng() * 9, rng() * 9, rng() * 9, rng() * 9], f: [0.7 + rng(), 0.7 + rng(), 0.7 + rng()], lib: V3(rng.dir()) }); }
    mol.sort((a, b) => a.d - b.d); }
  const NMOL = mol.length, HB = 0.9572, HA = 52.26 * DEG, H1 = new THREE.Vector3(Math.sin(HA) * HB, Math.cos(HA) * HB, 0), H2 = new THREE.Vector3(-Math.sin(HA) * HB, Math.cos(HA) * HB, 0);
  const oM = add(new THREE.InstancedMesh(sph, ballMat(0xffffff), NMOL), 20), hM = add(new THREE.InstancedMesh(sph, ballMat(0xffffff), NMOL * 2), 20), tv = new THREE.Vector3(), tq = new THREE.Quaternion(), tq2 = new THREE.Quaternion(), tc = new THREE.Color();
  oM.instanceMatrix.setUsage(THREE.DynamicDrawUsage); hM.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mol.forEach((m, i) => { const f = (i ? 0.7 : 1.15) * (1 - 0.8 * smoothstep(RM * 0.4, RM, m.d));      /* la molécule visée ressort, les voisines s'estompent avec la distance */ oM.setColorAt(i, tc.setRGB(0.62 * f, 0.06 * f, 0.05 * f)); hM.setColorAt(2 * i, tc.setRGB(0.78 * f, 0.78 * f, 0.82 * f)); hM.setColorAt(2 * i + 1, tc); });
  oM.instanceColor.needsUpdate = true; hM.instanceColor.needsUpdate = true;
  const hw1 = H1.clone().applyQuaternion(mol[0].q), hw2 = H2.clone().applyQuaternion(mol[0].q);
  function molUpdate(t, cd) {
    for (let i = 0; i < NMOL; i++) { const m = mol[i], a = i ? 1 : 0, x = m.c[0] + a * 0.22 * Math.sin(t * m.f[0] + m.ph[0]), y = m.c[1] + a * 0.22 * Math.sin(t * m.f[1] + m.ph[1]), z = m.c[2] + a * 0.22 * Math.sin(t * m.f[2] + m.ph[2]);
      const dep = x * cd.x + y * cd.y + z * cd.z, s = i ? 1 - smoothstep(1.5, 2.7, dep) : 1;                       // vue en coupe : les molécules placées entre l'œil et le point visé sont retirées
      tq2.setFromAxisAngle(m.lib, a * 0.3 * Math.sin(t * m.f[1] * 1.3 + m.ph[3])); tq.copy(tq2).multiply(m.q);
      m4.makeScale(1.52 * s, 1.52 * s, 1.52 * s).setPosition(x, y, z); oM.setMatrixAt(i, m4);
      tv.copy(H1).applyQuaternion(tq); m4.makeScale(1.1 * s, 1.1 * s, 1.1 * s).setPosition(x + tv.x, y + tv.y, z + tv.z); hM.setMatrixAt(2 * i, m4);
      tv.copy(H2).applyQuaternion(tq); m4.makeScale(1.1 * s, 1.1 * s, 1.1 * s).setPosition(x + tv.x, y + tv.y, z + tv.z); hM.setMatrixAt(2 * i + 1, m4); }
    oM.instanceMatrix.needsUpdate = true; hM.instanceMatrix.needsUpdate = true; }

  // --- nuage d'électrons de la molécule centrale : 10 électrons, densité approchée par des orbitales de Slater (charges effectives de Clementi et Raimondi)
  const NE = big ? 36000 : 15000, eP = new Float32Array(NE * 3), ePh = new Float32Array(NE);
  { const b = hw1.clone().add(hw2).normalize(), nrm = hw1.clone().cross(hw2).normalize(), c54 = Math.cos(54.75 * DEG), s54 = Math.sin(54.75 * DEG);
    const LOB = [hw1.clone().normalize(), hw2.clone().normalize(), b.clone().multiplyScalar(-c54).addScaledVector(nrm, s54), b.clone().multiplyScalar(-c54).addScaledVector(nrm, -s54)];
    for (let i = 0; i < NE; i++) { const u = rng(); let cx = 0, cy = 0, cz = 0, r, d;
      if (u < 0.2) { r = gam(3, A0 / (2 * 7.6579)); d = rng.dir(); }                                   // couche interne de l'oxygène : 2 électrons tout près du noyau
      else if (u < 0.87) { r = gam(5, A0 / 4.4532); const ax = LOB[(rng() * 4) | 0], n = rng.dir(); d = vnorm([ax.x + 0.8 * n[0], ax.y + 0.8 * n[1], ax.z + 0.8 * n[2]]); }      // couche externe : quatre lobes (deux liaisons, deux paires libres)
      else { const h = rng() < 0.5 ? hw1 : hw2; cx = h.x; cy = h.y; cz = h.z; r = gam(3, A0 / 2); d = rng.dir(); }                                                                   // part restée autour de chaque hydrogène
      eP[i * 3] = cx + d[0] * r; eP[i * 3 + 1] = cy + d[1] * r; eP[i * 3 + 2] = cz + d[2] * r; ePh[i] = rng(); } }
  const cloudMat = ptMat([0.25, 0.62, 1.0], 2.4), cloud = mkPts(eP, ePh, cloudMat, 30);
  const nucMat = ptMat([1.0, 0.9, 0.6], 6, 'a'), nucPts = mkPts(new Float32Array([0, 0, 0, hw1.x, hw1.y, hw1.z, hw2.x, hw2.y, hw2.z]), new Float32Array([1, 0.8, 0.8]), nucMat, 32);

  // --- noyau d'oxygène 16 : 8 protons et 8 neutrons en quatre groupes de 2 + 2 (description courante, pas une image)
  const TET = [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]].map(v => vnorm(v)), nuc = [];
  TET.forEach(a => { const q = new THREE.Quaternion().setFromAxisAngle(V3(rng.dir()), rng() * TAU); TET.forEach((b, j) => { tv.set(b[0], b[1], b[2]).applyQuaternion(q); nuc.push({ p: [a[0] * 2.11 + tv.x * 1.05, a[1] * 2.11 + tv.y * 1.05, a[2] * 2.11 + tv.z * 1.05], isP: j < 2, ph: rng() * 9, f: 2 + rng() * 2 }); }); });
  const P0 = nuc[0], QOFF = [-0.18, 0.10, 0.05], CP = [-QOFF[0], -QOFF[1], -QOFF[2]], CN = [CP[0] - P0.p[0], CP[1] - P0.p[1], CP[2] - P0.p[2]];       // centre du proton visé et centre du noyau, en fm, comptés depuis le quark visé
  const prot = nuc.filter(n => n.isP && n !== P0), neut = nuc.filter(n => !n.isP);
  const pM = add(new THREE.InstancedMesh(sphHi, ballMat(0xb8301f), prot.length), 40), nM = add(new THREE.InstancedMesh(sphHi, ballMat(0x6f7890), neut.length), 40), p0M = add(new THREE.Mesh(sphHi, ballMat(0xb8301f)), 41);
  pM.instanceMatrix.setUsage(THREE.DynamicDrawUsage); nM.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const nucleonAt = (n, t, o) => { o[0] = n.p[0] + 0.1 * Math.sin(t * n.f + n.ph); o[1] = n.p[1] + 0.1 * Math.sin(t * n.f * 1.3 + n.ph * 2); o[2] = n.p[2] + 0.1 * Math.cos(t * n.f * 0.8 + n.ph); return o; }, np = [0, 0, 0];

  // --- intérieur du proton : nuage suivant la répartition de charge mesurée, trois quarks, tubes de gluons, paires éphémères (schéma)
  const NPC = big ? 7000 : 3500, pcP = new Float32Array(NPC * 3), pcPh = new Float32Array(NPC);
  for (let i = 0; i < NPC; i++) { const r = gam(3, RP / Math.sqrt(12)), d = rng.dir(); pcP[i * 3] = d[0] * r; pcP[i * 3 + 1] = d[1] * r; pcP[i * 3 + 2] = d[2] * r; pcPh[i] = rng(); }
  const pcMat = ptMat([1.0, 0.55, 0.3], 2.2), pCloud = mkPts(pcP, pcPh, pcMat, 50);
  const qP = new Float32Array(9), qC = new Float32Array(9), qMat = ptMat([1, 1, 1], 16, 'c'), quarks = mkPts(qP, new Float32Array([1, 1, 1]), qMat, 54, qC);
  const TUBE = 30, tubeP = new Float32Array(3 * (TUBE - 1) * 2 * 3), tubeG = new THREE.BufferGeometry(); tubeG.setAttribute('position', new THREE.BufferAttribute(tubeP, 3));
  const tubeMat = new THREE.LineBasicMaterial({ color: new THREE.Color(1.0, 0.8, 0.35), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false }), tubes = add(new THREE.LineSegments(tubeG, tubeMat), 52);
  const NSEA = 12, seaP = new Float32Array(NSEA * 6), seaA = new Float32Array(NSEA * 2), seaC = new Float32Array(NSEA * 6), seaMat = ptMat([1, 1, 1], 7, 'c'), sea = mkPts(seaP, seaA, seaMat, 53, seaC);
  for (let k = 0; k < NSEA; k++) { seaC.set([0.3, 0.9, 1.0, 1.0, 0.35, 0.9], k * 6); }
  const QCOL = [[1.0, 0.25, 0.2], [0.25, 1.0, 0.3], [0.3, 0.45, 1.0]], qpos = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], hsh = x => { const s = Math.sin(x * 127.1) * 43758.5453; return s - Math.floor(s); };
  function protonUpdate(t) {
    qpos[0][0] = QOFF[0]; qpos[0][1] = QOFF[1]; qpos[0][2] = QOFF[2];
    qpos[1][0] = 0.30 * Math.cos(t * 0.9 + 1) + 0.12; qpos[1][1] = 0.30 * Math.sin(t * 1.1 + 2) - 0.1; qpos[1][2] = 0.24 * Math.sin(t * 0.7);
    qpos[2][0] = -0.05 + 0.26 * Math.sin(t * 0.8 + 4); qpos[2][1] = -0.22 + 0.2 * Math.cos(t * 1.0); qpos[2][2] = 0.3 * Math.cos(t * 0.6 + 1);
    const ph = t / 1.6, sh = Math.floor(ph), mix = smoothstep(0.75, 1, ph - sh), J = [(qpos[0][0] + qpos[1][0] + qpos[2][0]) / 3, (qpos[0][1] + qpos[1][1] + qpos[2][1]) / 3, (qpos[0][2] + qpos[1][2] + qpos[2][2]) / 3];
    for (let i = 0; i < 3; i++) { const a = QCOL[(i + sh) % 3], b = QCOL[(i + sh + 1) % 3]; qP.set(qpos[i], i * 3); qC[i * 3] = lerp(a[0], b[0], mix); qC[i * 3 + 1] = lerp(a[1], b[1], mix); qC[i * 3 + 2] = lerp(a[2], b[2], mix); }      // les quarks échangent leurs « couleurs » en permanence
    let o = 0; for (let i = 0; i < 3; i++) { const q = qpos[i]; let px = J[0], py = J[1], pz = J[2]; for (let s = 1; s < TUBE; s++) { const u = s / (TUBE - 1), w = 0.012 * Math.sin(u * Math.PI) * Math.sin(u * 16 - t * 5 + i * 2), x = lerp(J[0], q[0], u) + w, y = lerp(J[1], q[1], u) - w, z = lerp(J[2], q[2], u) + w * 0.6; tubeP[o++] = px; tubeP[o++] = py; tubeP[o++] = pz; tubeP[o++] = x; tubeP[o++] = y; tubeP[o++] = z; px = x; py = y; pz = z; } }
    for (let k = 0; k < NSEA; k++) { const c = t * 0.55 + k * 0.37, cy = Math.floor(c), u = c - cy, r = 0.15 + 0.55 * hsh(cy * 3.1 + k), th = TAU * hsh(cy * 1.7 + k * 5.3), zz = 2 * hsh(cy * 2.3 + k * 9.1) - 1, sx = Math.sqrt(1 - zz * zz), bx = r * sx * Math.cos(th), by = r * sx * Math.sin(th), bz = r * zz, sp = 0.07 * u;
      seaP.set([bx + sp, by, bz, bx - sp, by, bz], k * 6); seaA[k * 2] = seaA[k * 2 + 1] = Math.sin(Math.PI * u); }
    quarks.geometry.attributes.position.needsUpdate = true; quarks.geometry.attributes.aC.needsUpdate = true; tubeG.attributes.position.needsUpdate = true; sea.geometry.attributes.position.needsUpdate = true; sea.geometry.attributes.aPh.needsUpdate = true; return J; }
  // le quark visé, seul, quand on descend plus bas : un point sans taille mesurable
  const q1Mat = ptMat([1.0, 0.5, 0.4], 14, 'a'), q1 = mkPts(new Float32Array(3), new Float32Array([1]), q1Mat, 56);

  // --- repères : un cercle par puissance de dix, et des cercles nommés (limites mesurées)
  const circ = new Float32Array(97 * 3); for (let i = 0; i <= 96; i++) { circ[i * 3] = Math.cos(i / 96 * TAU); circ[i * 3 + 1] = Math.sin(i / 96 * TAU); }
  const cg = new THREE.BufferGeometry(); cg.setAttribute('position', new THREE.BufferAttribute(circ, 3));
  const ring = (col, ord) => add(new THREE.Line(cg, new THREE.LineBasicMaterial({ color: new THREE.Color(col[0], col[1], col[2]), transparent: true, opacity: 0, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending })), ord);
  const dec = [0, 1, 2, 3, 4, 5].map(() => ring([0.35, 0.45, 0.6], 60));
  const MARK = [['weak', 2.455e-18, [1.0, 0.7, 0.25]], ['lim', 4.3e-19, [1.0, 0.7, 0.25]], ['lhc', 2e-20, [1.0, 0.7, 0.25]]].map(a => ({ key: a[0], r: a[1], o: ring(a[2], 61) }));
  /* R13 : plus de bouillonnement « vue d'artiste » à la longueur de Planck : le zoom s'arrête à 10⁻²⁰ m. */

  const mine = new Set(all), hidden = new Set(), far = new Set();
  const cd = new THREE.Vector3(), cu = new THREE.Vector3(), P = M.pos, setP = (k, x, y, z) => { const a = P[k] || (P[k] = [0, 0, 0]); a[0] = x; a[1] = y; a[2] = z; };
  M.update = F => {
    const lr = F.lrT, k = lr === undefined ? 0 : fadeOut(lr, 2.2, 3.3); M.k = k;
    { const e = R.bodies && R.bodies.earth; if (e && e.u && e.u.uOcean) e.u.uOcean.value = 0.1 + 0.9 * smoothstep(5.6, 7.1, lr === undefined ? 9 : lr); }      // de près, le reflet du Soleil sur l'océan éblouirait toute l'image
    // fond opaque : le décor astronomique n'est plus dessiné du tout (il est figé, et une valeur invalide dans son image contaminerait la nôtre)
    if (k >= 0.999) { for (const o of scene.children) if (o.visible && !mine.has(o)) { o.visible = false; hidden.add(o); } } else if (hidden.size) { hidden.forEach(o => { o.visible = true; }); hidden.clear(); }
    // à moins de 6 000 km du sol, la Terre remplit l'image : étoiles, galaxie et orbites ne sont plus dessinées (leurs points, devenus énormes, ralentissaient tout)
    if (lr !== undefined && lr < 6.35 && k < 0.999) { for (const o of scene.children) if (o.visible && !mine.has(o) && o.scale.x > 3e5 && !(o.material && o.material.uniforms && o.material.uniforms.uOcean)) { o.visible = false; far.add(o); } } else if (far.size) { if (k < 0.999) far.forEach(o => { o.visible = true; }); far.clear(); }
    if (k < 0.003) { if (back.visible) for (const o of all) o.visible = false; return; }
    const s = F.sT, t = F.wall || 0, dpr = R.dpr || 1, bc = backCol(lr); back.visible = true; backMat.opacity = k; backMat.color.setRGB(bc[0], bc[1], bc[2]);
    cd.copy(camera.position).normalize(); cu.set(0, 1, 0).applyQuaternion(camera.quaternion);
    const nx = CN[0] * FM, ny = CN[1] * FM, nz = CN[2] * FM, place = (o, unit) => { o.position.set(nx * s, ny * s, nz * s); o.scale.setScalar(unit * s); };
    // gouttelette
    { const v = vis(lr, -3.9, 0.9, 0.5); drop.visible = v > 0.01; if (drop.visible) { drop.scale.setScalar(1e-3 * s); dropU.uOp.value = v; } setP('drop', cu.x * 1.15e-3, cu.y * 1.15e-3, cu.z * 1.15e-3); }
    // molécules
    { const v = fadeOut(lr, -8.75, -8.45) * fadeIn(lr, -10.2, -9.8); oM.visible = hM.visible = v > 0.01; if (oM.visible) { molUpdate(t * 1.4, cd); place(oM, ANG); place(hM, ANG); oM.material.opacity = hM.material.opacity = v; }
      setP('mol', nx + cu.x * 2.3e-10, ny + cu.y * 2.3e-10, nz + cu.z * 2.3e-10); setP('O', nx, ny, nz); setP('H1', nx + hw1.x * ANG, ny + hw1.y * ANG, nz + hw1.z * ANG); setP('H2', nx + hw2.x * ANG, ny + hw2.y * ANG, nz + hw2.z * ANG); setP('nuc', nx, ny, nz); }
    // nuage d'électrons et noyaux vus comme des points
    { const v = vis(lr, -12.9, -9.55, 0.3); cloud.visible = v > 0.01; if (cloud.visible) { place(cloud, ANG); cloudMat.uniforms.uOp.value = v * (big ? 0.5 : 0.8); cloudMat.uniforms.uPx.value = 2.4 * dpr; cloudMat.uniforms.uT.value = t; }
      const w = vis(lr, -12.5, -9.7, 0.3); nucPts.visible = w > 0.01; if (nucPts.visible) { place(nucPts, ANG); nucMat.uniforms.uOp.value = w; nucMat.uniforms.uPx.value = 6 * dpr; } }
    // noyau
    { const v = vis(lr, -16.2, -12.3, 0.3); pM.visible = nM.visible = v > 0.01; const v0 = v * fadeIn(lr, -14.98, -14.6); p0M.visible = v0 > 0.01;
      if (pM.visible) { prot.forEach((n, i) => { nucleonAt(n, t, np); m4.makeScale(RP, RP, RP).setPosition(np[0], np[1], np[2]); pM.setMatrixAt(i, m4); }); neut.forEach((n, i) => { nucleonAt(n, t, np); m4.makeScale(RP, RP, RP).setPosition(np[0], np[1], np[2]); nM.setMatrixAt(i, m4); if (!i) setP('n', (CN[0] + np[0]) * FM, (CN[1] + np[1]) * FM, (CN[2] + np[2]) * FM + RP * FM); });
        pM.instanceMatrix.needsUpdate = true; nM.instanceMatrix.needsUpdate = true; place(pM, FM); place(nM, FM); pM.material.opacity = nM.material.opacity = v * (0.12 + 0.88 * fadeIn(lr, -15.2, -14.75)); }
      if (p0M.visible) { p0M.position.set(CP[0] * FM * s, CP[1] * FM * s, CP[2] * FM * s); p0M.scale.setScalar(RP * FM * s); p0M.material.opacity = v0; }
      setP('p', CP[0] * FM, CP[1] * FM, CP[2] * FM + RP * FM); }
    // intérieur du proton
    { const v = vis(lr, -18.0, -14.95, 0.3), on = v > 0.01; pCloud.visible = quarks.visible = tubes.visible = sea.visible = on;
      if (on) { const J = protonUpdate(t * 1.2); for (const o of [pCloud, quarks, tubes, sea]) { o.position.set(CP[0] * FM * s, CP[1] * FM * s, CP[2] * FM * s); o.scale.setScalar(FM * s); }
        pcMat.uniforms.uOp.value = v * 0.35; pcMat.uniforms.uPx.value = 2.2 * dpr; pcMat.uniforms.uT.value = t; qMat.uniforms.uOp.value = v * 1.6; qMat.uniforms.uPx.value = 16 * dpr; seaMat.uniforms.uOp.value = v * 0.9; seaMat.uniforms.uPx.value = 7 * dpr; tubeMat.opacity = v * 0.75;
        for (let i = 0; i < 3; i++) setP('q' + i, (CP[0] + qpos[i][0]) * FM, (CP[1] + qpos[i][1]) * FM, (CP[2] + qpos[i][2]) * FM); setP('glu', (CP[0] + J[0]) * FM, (CP[1] + J[1]) * FM, (CP[2] + J[2]) * FM); } }
    { const v = vis(lr, -22.0, -16.9, 0.4); q1.visible = v > 0.01; if (q1.visible) { q1Mat.uniforms.uOp.value = v * 1.5; q1Mat.uniforms.uPx.value = 14 * dpr; } }
    // cercles repères
    { const dk = vis(lr, -36, -18.4, 0.5), k0 = Math.floor(lr) - 2; dec.forEach((o, j) => { const r = Math.pow(10, k0 + j) * s, a = dk * smoothstep(0.08, 0.5, r) * (1 - smoothstep(6, 14, r)); o.visible = a > 0.01; if (o.visible) { o.quaternion.copy(camera.quaternion); o.scale.setScalar(r); o.material.opacity = a * 0.5; } });
      for (const mk of MARK) { const r = mk.r * s, a = smoothstep(0.06, 0.4, r) * (1 - smoothstep(7, 16, r)); mk.o.visible = a > 0.01; if (mk.o.visible) { mk.o.quaternion.copy(camera.quaternion); mk.o.scale.setScalar(r); mk.o.material.opacity = a * 0.9; } setP(mk.key, cu.x * mk.r, cu.y * mk.r, cu.z * mk.r); } }
  };
  M.count = { mol: NMOL, electrons: NE };
  return M;
}

function createRenderer(canvas, Q, generated) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance', stencil: false });
  const gl = renderer.getContext();
  renderer.autoClear = true; renderer.setClearColor(0x000000, 1);
  gl.getExtension('EXT_color_buffer_float'); gl.getExtension('EXT_color_buffer_half_float'); gl.getExtension('OES_texture_float_linear');
  const isGL2 = renderer.capabilities.isWebGL2;
  const maxPoint = gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE)[1] || 64;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.5, 1e7);
  const R = { renderer, scene, camera, dpr: 1, w: 1, h: 1, bloom: Q.bloom, hdr: true, labelsOut: [] };
  const additive = { transparent: true, depthTest: false, depthWrite: false, blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor };
  const U = v => ({ value: v });
  const mk = (sh, uniforms, extra) => new THREE.ShaderMaterial(Object.assign({ vertexShader: sh.v, fragmentShader: sh.f, uniforms }, additive, extra || {}));
  const pts = (attrs, mat, order) => {
    const g = new THREE.BufferGeometry();
    for (const k in attrs) g.setAttribute(k, new THREE.BufferAttribute(attrs[k][0], attrs[k][1]));
    const p = new THREE.Points(g, mat); p.frustumCulled = false; p.renderOrder = order; p.matrixAutoUpdate = true; scene.add(p); return p;
  };
  const M = DATA.M_GAL2ECL;
  const qGal = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().set(M[0][0], M[0][1], M[0][2], 0, M[1][0], M[1][1], M[1][2], 0, M[2][0], M[2][1], M[2][2], 0, 0, 0, 0, 1));
  const ngp = new THREE.Vector3(M[0][2], M[1][2], M[2][2]);
  const qFrameGal = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), ngp);
  R.qFrameGal = qFrameGal;

  /* ---- couches de points ---- */
  const G = generated;
  // toile cosmique et très grandes échelles (Mpc comobiles)
  let web = null, far = null, webU = null, farU = null;
  R.addSim = (W, Fr) => { const SW = W.N / (W.RW - 16), SF = Fr.N / (Fr.RMAX - Fr.R0);
    webU = { uD: U(1), uPx: U(1), uOpacity: U(1), uHorizon: U(14000), uAge: U(13.8), uMinPx: U(1), uMaxPx: U(64), uSw: U(SW), uSf: U(SF), uRW: U(W.RW), uCR: U(100) };
    web = pts({ position: [W.q, 3], aPsi: [W.psi, 3], aEig: [W.eig, 3], aRnd: [W.rnd, 4] }, mk(SH.web, webU), 2);
    farU = { uPx: U(1), uOpacity: U(1), uHorizon: U(14000), uAge: U(13.8), uMinPx: U(1), uSw: U(SW), uSf: U(SF), uRW: U(W.RW), uCR: U(100) };
    far = pts({ position: [Fr.pos, 3], aRnd: [Fr.rnd, 2] }, mk(SH.far, farU), 1); };
  // repères réels du flot de Hubble : rendus comme des galaxies/amas plus brillants
  const lm = DATA.FAR.filter(f => f.k !== 'void');
  const lmPos = new Float32Array(lm.length * 3), lmCol = new Float32Array(lm.length * 3), lmLook = new Float32Array(lm.length * 2), lmOm = new Float32Array(lm.length * 2);
  lm.forEach((f, i) => { lmPos.set(f.pos, i * 3); lmCol.set(f.k === 'cluster' ? [1.0, 0.82, 0.55] : [0.8, 0.86, 1.0], i * 3); lmLook.set([f.k === 'cluster' ? clamp(f.sg * 0.1, 0.7, 2.2) : 0.06, f.k === 'cluster' ? 0.26 : 0.8], i * 2); });
  const galU = () => ({ uT1: U(0), uT2: U(0), uPx: U(1), uOpacity: U(1), uMinPx: U(1), uMaxPx: U(64), uFloor: U(0), uBigPx: U(64), uExag: U(1), uStarCap: U(2.4), uInside: U(0), uShift: U(new THREE.Vector3()), uShift2: U(new THREE.Vector3()), uG2: U(1), uHide: U(new THREE.Vector3(1e9, 1e9, 1e9)), uHideK: U(0) });
  const lmU = galU();
  const landmarks = pts({ position: [lmPos, 3], aOm: [lmOm, 2], aCol: [lmCol, 3], aLook: [lmLook, 2] }, mk(SH.galaxy, lmU), 3);
  // galaxies proches à distance mesurée (Karachentsev 2013), en Mpc comobiles
  const nRaw = new Float32Array(b64ToBytes(DATA.NEAR).buffer), nN = DATA.NEAR_N, nPos = new Float32Array(nN * 3), nCol = new Float32Array(nN * 3), nLook = new Float32Array(nN * 2);
  for (let i = 0; i < nN; i++) { nPos.set([nRaw[i * 5], nRaw[i * 5 + 1], nRaw[i * 5 + 2]], i * 3); nCol.set([0.8, 0.87, 1.0], i * 3); nLook.set([nRaw[i * 5 + 3], clamp((-nRaw[i * 5 + 4] - 9) / 11, 0.15, 1)], i * 2); }
  const nearU = galU();
  const near = pts({ position: [nPos, 3], aOm: [new Float32Array(nN * 2), 2], aCol: [nCol, 3], aLook: [nLook, 2] }, mk(SH.galaxy, nearU), 3);
  // relevés de décalages vers le rouge : 2MRS, puis 6dF/2dF/SDSS/DESI, puis quasars. Direction fixe, distance recalculée selon la cosmologie choisie
  const sv = new Uint16Array(b64ToBytes(DATA.SURV).buffer), svN = sv.length / 3, svDir = new Float32Array(svN * 3), svInfo = new Float32Array(svN * 3), svDist = new Float32Array(svN), svU = new Float32Array(svN);
  { const lz = Math.log(1 + DATA.SURV_ZMAX), n1 = DATA.SURV_N[0], n2 = n1 + DATA.SURV_N[1];
    for (let i = 0; i < svN; i++) { const lon = sv[i * 3] / 65535 * TAU, lat = (sv[i * 3 + 1] / 65535 - 0.5) * Math.PI, cl = Math.cos(lat); svDir.set([cl * Math.cos(lon), cl * Math.sin(lon), Math.sin(lat)], i * 3); svU[i] = sv[i * 3 + 2] / 65535; svInfo.set([Math.exp(svU[i] * lz) - 1, ((Math.imul(i + 1, 2654435761) >>> 0) / 4294967296), i < n1 ? 0 : i < n2 ? 1 : 2], i * 3); } }
  const survU = { uPx: U(1), uOpacity: U(1), uMinPx: U(1), uCR: U(100), uHorizon: U(14000), uAge: U(13.8), uKeep: U(Q.keep || 1) };
  const ZC = DATA.ZCOL, zv = a => Array.from({ length: ZC.n }, (_, i) => new THREE.Vector3(a[i * 3], a[i * 3 + 1], a[i * 3 + 2])); survU.uZG = U(zv(ZC.gal)); survU.uZQ = U(zv(ZC.qso)); survU.uZM = U(new THREE.Vector2(Math.log(1 + ZC.zg), Math.log(1 + ZC.zq)));      /* S3 : partagés avec les tuiles de galaxies */
  const surv = pts({ position: [svDir, 3], aDist: [svDist, 1], aInfo: [svInfo, 3] }, mk(SH.surv, survU), 2);
  R.pick = { nPos, nLook, nN, svDir, svDist, svInfo, svN, keep: Q.keep || 1 };
  R.setSurvey = lut => { const K = lut.length - 1; for (let i = 0; i < svN; i++) { const x = svU[i] * K, k = Math.min(x | 0, K - 1); svDist[i] = lut[k] + (lut[k + 1] - lut[k]) * (x - k); } surv.geometry.attributes.aDist.needsUpdate = true; };
  // halo de matière noire, Groupe local, Voie lactée (kpc)
  const lgU = galU(); lgU.uSh = U(Array.from({ length: 104 }, () => new THREE.Vector3())); lgU.uAx = U(Array.from({ length: 104 }, (_, i) => new THREE.Vector3(G.lg.axes[i * 3], G.lg.axes[i * 3 + 1], G.lg.axes[i * 3 + 2])));      // axe de rotation de chaque galaxie à disque (nul : pas de rotation montrée)      // déplacement propre de chaque galaxie du Groupe local (orbite calculée)
  const localGroup = pts({ position: [G.lg.pos, 3], aOm: [G.lg.om, 2], aCol: [G.lg.col, 3], aLook: [G.lg.look, 2], aCen: [G.lg.cen, 3], aGrp: [G.lg.grp, 1], aId: [G.lg.id, 1] }, mk(SH.galaxy, lgU), 5);
  // Andromède : galaxie à part entière (elle tourne et se déplace), et galaxie elliptique qui naît d'une éventuelle fusion
  const m31U = galU(), m31 = pts({ position: [G.m31.pos, 3], aOm: [G.m31.om, 2], aCol: [G.m31.col, 3], aLook: [G.m31.look, 2] }, mk(SH.galaxy, m31U), 5);
  { const sp = mulM(M, DATA.M31.spin); m31.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), new THREE.Vector3(-sp[0], -sp[1], -sp[2]).normalize()); }
  { const e = new THREE.Matrix4().makeRotationFromQuaternion(m31.quaternion).elements, Qm = [[e[0], e[4], e[8]], [e[1], e[5], e[9]], [e[2], e[6], e[10]]];
    R.m31Rot = [0, 1, 2].map(i => [0, 1, 2].map(j => M[0][i] * Qm[0][j] + M[1][i] * Qm[1][j] + M[2][i] * Qm[2][j])); }      // repère propre d'Andromède -> axes galactiques
  let dyn = null, dynU = null;
  R.setDyn = D => { if (dyn) { scene.remove(dyn); dyn.geometry.dispose(); } dynU = galU(); dyn = pts({ position: [D.out, 3], aOm: [new Float32Array(D.n * 2), 2], aCol: [D.col, 3], aLook: [D.look, 2] }, mk(SH.galaxy, dynU), 6); dyn.quaternion.copy(qGal); };
  const mwU = galU();
  const galaxy = pts({ position: [G.gal.pos, 3], aOm: [G.gal.om, 2], aCol: [G.gal.col, 3], aLook: [G.gal.look, 2] }, mk(SH.galaxy, mwU), 6);
  galaxy.quaternion.copy(qGal);
  // étoiles : champ local généré, catalogue réel, Soleil vu comme une étoile (années-lumière)
  const starU = () => ({ uUnitToPc: U(1), uExpo: U(0), uOpacity: U(1), uDpr: U(1), uEvolve: U(0), uT: U(0), uFlash: U(1e-6), uVt: U(0), uMcut: U(99), uTgt: U(new THREE.Vector3()), uTgtR: U(0) });
  // amas d'étoiles réels : 145 amas globulaires (Harris) et 1 867 amas ouverts (Cantat-Gaudin 2020), en années-lumière
  const cRaw = new Float32Array(b64ToBytes(DATA.CLUSTERS).buffer), cN = cRaw.length / 5, cPos = new Float32Array(cN * 3), cMag = new Float32Array(cN), cCol = new Float32Array(cN * 3);
  for (let i = 0; i < cN; i++) { cPos.set([cRaw[i * 5], cRaw[i * 5 + 1], cRaw[i * 5 + 2]], i * 3); cMag[i] = cRaw[i * 5 + 3]; cCol.set(bvToRgb(cRaw[i * 5 + 4]), i * 3); }
  const clusU = starU(); R.clu = { pos: cPos, mag: cMag, N: cN };
  const clusters = pts({ position: [cPos, 3], aMag: [cMag, 1], aCol: [cCol, 3] }, mk(SH.star, clusU), 7);
  // XS : étoiles qui frôlent le Soleil (Bailer-Jones 2022) absentes du catalogue principal ; elles y sont ajoutées, avec leur mouvement
  const XS = (DATA.PASSERS || []).filter(o => o.i < 0), sN0 = DATA.STARS_N, sN = sN0 + XS.length, sGeo = new Uint16Array(b64ToBytes(DATA.STARS_GEO).buffer), sAux = b64ToBytes(DATA.STARS_AUX), sPos = new Float32Array(sN * 3);
  XS.forEach((o, k) => sPos.set(o.p, (sN0 + k) * 3));
  for (let i = 0; i < sN0; i++) { const lon = sGeo[i * 3] / 65535 * TAU, lat = (sGeo[i * 3 + 1] / 65535 - 0.5) * Math.PI, d = Math.pow(10, sGeo[i * 3 + 2] / 65535 * 5.5 - 1), cl = Math.cos(lat); sPos.set([d * cl * Math.cos(lon), d * cl * Math.sin(lon), d * Math.sin(lat)], i * 3); }
  const sMag = new Float32Array(sN), sCol = new Float32Array(sN * 3);
  for (let i = 0; i < sN0; i++) { sMag[i] = sAux[i * 2] / 8 - 10; sCol.set(bvToRgb(sAux[i * 2 + 1] / 100 - 0.5), i * 3); }
  XS.forEach((o, k) => { sMag[sN0 + k] = o.mv; sCol.set(bvToRgb(o.bv), (sN0 + k) * 3); });
  R.starPos = sPos;
  const starsU = starU();
  // vie et mouvement de chaque étoile : destin estimé d'après l'éclat et la couleur, vitesse mesurée
  const sHip = new Uint32Array(sN), sLife = new Float32Array(sN * 3), sFate = new Float32Array(sN), sMass = new Float32Array(sN), sCls = new Uint8Array(sN), sBv = new Float32Array(sN);
  sHip.set(new Uint32Array(b64ToBytes(DATA.STARS_HIP).buffer).subarray(0, sN0));
  for (let i = 0; i < sN; i++) { sBv[i] = i < sN0 ? sAux[i * 2 + 1] / 100 - 0.5 : XS[i - sN0].bv; const L = starLife(sMag[i], sBv[i], i, sHip[i]); sLife.set([clamp(L[0], -2e5, 2e5), clamp(L[1], -2e5, 2e5), clamp(L[2], -2e5, 2e5)], i * 3); sFate[i] = L[3]; sMass[i] = L[4]; sCls[i] = L[5]; }
  const vq = new Int16Array(sN * 3), Mg = DATA.M_GAL2ECL; vq.set(new Int16Array(b64ToBytes(DATA.STARS_VEL).buffer).subarray(0, sN0 * 3)); XS.forEach((o, k) => { for (let a = 0; a < 3; a++) vq[(sN0 + k) * 3 + a] = Math.round(20 * (Mg[0][a] * o.v[0] + Mg[1][a] * o.v[1] + Mg[2][a] * o.v[2])); });
  const K = initStarKin(sPos, sN, DATA.SGRA_GAL.map(x => -x * GAL.R0), vq); R.K = K; orbInit(K, DATA.SGRA_GAL.map(x => -x * GAL.R0));
  // trajectoire publiée (instant, distance et vitesse du passage) pour chaque étoile frôleuse, ajoutée ou déjà présente
  K.lin = new Uint8Array(sN);
  R.passers = (DATA.PASSERS || []).map(o => { const i = o.i >= 0 ? o.i : sN0 + XS.indexOf(o); K.lin[i] = 1; for (let a = 0; a < 3; a++) { K.p0[i * 3 + a] = o.p[a]; sPos[i * 3 + a] = o.p[a]; K.ve[i * 3 + a] = o.v[a] * KMS_LY_YR; } K.vkms[i] = o.vk; sMass[i] = o.m; if (!DATA.STAR_NAMES[i]) DATA.STAR_NAMES[i] = o.n; return Object.assign({ idx: i }, o); });
  // les étoiles frôleuses sont dessinées par le catalogue principal : leurs copies dans les autres catalogues Gaia sont éteintes (même direction à 0,02 degré près, même distance à 1,2 % près)
  const PNOW = (DATA.PASSERS || []).filter(o => o.G <= 13.2).map(o => { const d = Math.hypot(o.now[0], o.now[1], o.now[2]); return [o.now[0], o.now[1], o.now[2], 0.012 * d + 0.03, d]; });
  const isPasser = (x, y, z) => { for (let q = 0; q < PNOW.length; q++) { const w = PNOW[q]; if (Math.abs(x - w[0]) < w[3] && Math.abs(y - w[1]) < w[3] && Math.abs(z - w[2]) < w[3]) { const d = Math.hypot(x, y, z); if ((x * w[0] + y * w[1] + z * w[2]) / (d * w[4]) > 1 - 8e-8 && Math.abs(d / w[4] - 1) < 0.012) return true; } } return false; }; R.star = { N: sN, mag: sMag, bv: sBv, hip: sHip, life: sLife, fate: sFate, mass: sMass, cls: sCls };
  const stars = pts({ position: [sPos, 3], aMag: [sMag, 1], aCol: [sCol, 3], aLife: [sLife, 3], aFate: [sFate, 1] }, mk(SH.star, starsU), 8); starsU.uEvolve.value = 1;
  let starCursor = 0, starPassT = 1e99, starDone = 0;
  // --- Gaia DR3 : toutes les étoiles plus faibles que le premier catalogue, jusqu'à la magnitude limite du jeu de données
  const gN = Math.round(DATA.GAIA_N * (Q.gaia || 1)), gGeo = new Uint16Array(b64ToBytes(DATA.GAIA_GEO).buffer), gAux = b64ToBytes(DATA.GAIA_AUX), gPos = new Float32Array(gN * 3), gMag = new Float32Array(gN), gCol = new Float32Array(gN * 3), gBv = new Float32Array(gN), gLife = new Float32Array(gN * 3), gFate = new Float32Array(gN), gMass = new Float32Array(gN), gCls = new Uint8Array(gN);
  for (let i = 0; i < gN; i++) { const lon = gGeo[i * 3] / 65535 * TAU, lat = (gGeo[i * 3 + 1] / 65535 - 0.5) * Math.PI, d = Math.pow(10, gGeo[i * 3 + 2] / 65535 * 5), cl = Math.cos(lat); gPos[i * 3] = d * cl * Math.cos(lon); gPos[i * 3 + 1] = d * cl * Math.sin(lon); gPos[i * 3 + 2] = d * Math.sin(lat);
    gMag[i] = gAux[i * 2] / 8 - 10; gBv[i] = gAux[i * 2 + 1] / 80 - 0.5; gCol.set(bvToRgb(gBv[i]), i * 3); const L = starLife(gMag[i], gBv[i], i + 100000, 0); gLife[i * 3] = clamp(L[0], -2e5, 2e5); gLife[i * 3 + 1] = clamp(L[1], -2e5, 2e5); gLife[i * 3 + 2] = clamp(L[2], -2e5, 2e5); gFate[i] = L[3]; gMass[i] = L[4]; gCls[i] = L[5]; if (isPasser(gPos[i * 3], gPos[i * 3 + 1], gPos[i * 3 + 2])) gMag[i] = 40; }
  const K2 = initStarKin(gPos, gN, DATA.SGRA_GAL.map(x => -x * GAL.R0), new Int8Array(b64ToBytes(DATA.GAIA_VEL).buffer), 0.5, true), stars2U = starU();
  const stars2 = pts({ position: [gPos, 3], aMag: [gMag, 1], aCol: [gCol, 3], aLife: [gLife, 3], aFate: [gFate, 1] }, mk(SH.star, stars2U), 8); stars2U.uEvolve.value = 1;
  R.star2 = { N: gN, pos: gPos, mag: gMag, bv: gBv, life: gLife, fate: gFate, mass: gMass, cls: gCls, K: K2 }; let star2Cursor = 0, star2PassT = 1e99, star2Done = gN;
  // --- données en flux : étoiles et galaxies supplémentaires, reçues par morceaux après le démarrage.
  //     Rien n'est recalculé par le processeur à chaque image : le déplacement des étoiles (position + vitesse × temps) est fait par la carte graphique.
  R.tiles = [];
  const CI_RGB = new Uint8Array(256 * 3); for (let c = 0; c < 256; c++) { const rgb = bvToRgb(c / 80 - 0.5); for (let k = 0; k < 3; k++) CI_RGB[c * 3 + k] = Math.round(clamp(rgb[k], 0, 1) * 255); }
  const dynAttr = (g, name, arr, size, norm) => { const a = new THREE.BufferAttribute(arr, size, !!norm); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); };
  const tileObj = (T, sh, order) => { const o = T.obj = new THREE.Points(T.g, mk(sh, T.u)); o.frustumCulled = false; o.renderOrder = order; o.visible = false; scene.add(o); T.g.setDrawRange(0, 0); R.tiles.push(T); return T; };
  R.addStarTile = cap => {
    const T = { kind: 'star', rec: 11, cap, n: 0, sent: 0, draw: 0, pos: new Float32Array(cap * 3), mag: new Float32Array(cap), ci: new Uint8Array(cap), vel: new Int8Array(cap * 3), col: new Uint8Array(cap * 3), u: starU(), attrs: [['position', 3], ['aMag', 1], ['aCol', 3], ['aVel', 3]], g: new THREE.BufferGeometry() };
    dynAttr(T.g, 'position', T.pos, 3); dynAttr(T.g, 'aMag', T.mag, 1); dynAttr(T.g, 'aCol', T.col, 3, true); dynAttr(T.g, 'aVel', T.vel, 3);
    T.append = (b, off, cnt) => { const pos = T.pos, mag = T.mag, ci = T.ci, vel = T.vel, col = T.col;
      for (let k = 0, o = off, i = T.n; k < cnt; k++, o += 11, i++) {
        const lon = (b[o] | b[o + 1] << 8) / 65535 * TAU, lat = ((b[o + 2] | b[o + 3] << 8) / 65535 - 0.5) * Math.PI, d = Math.pow(10, (b[o + 4] | b[o + 5] << 8) / 65535 * 5), cl = Math.cos(lat), j = i * 3, c = b[o + 7];
        pos[j] = d * cl * Math.cos(lon); pos[j + 1] = d * cl * Math.sin(lon); pos[j + 2] = d * Math.sin(lat); mag[i] = b[o + 6] / 8 - 10;
        if (isPasser(pos[j], pos[j + 1], pos[j + 2])) mag[i] = 40; /* étoile frôleuse déjà dessinée par le catalogue principal : pas de doublon */ ci[i] = c; col[j] = CI_RGB[c * 3]; col[j + 1] = CI_RGB[c * 3 + 1]; col[j + 2] = CI_RGB[c * 3 + 2];
        vel[j] = b[o + 8] << 24 >> 24; vel[j + 1] = b[o + 9] << 24 >> 24; vel[j + 2] = b[o + 10] << 24 >> 24; }
      T.n += cnt; };
    return tileObj(T, SH.star, 8); };
  R.addGalTile = cap => {
    const T = { kind: 'gal', rec: 6, cap, n: 0, sent: 0, draw: 0, dir: new Float32Array(cap * 3), dist: new Float32Array(cap), info: new Float32Array(cap * 3), zu: new Float32Array(cap), u: { uPx: U(1), uOpacity: U(1), uMinPx: U(1), uCR: U(100), uHorizon: U(14000), uAge: U(13.8), uKeep: U(1), uZG: survU.uZG, uZQ: survU.uZQ, uZM: survU.uZM }, attrs: [['position', 3], ['aDist', 1], ['aInfo', 3]], g: new THREE.BufferGeometry() };
    dynAttr(T.g, 'position', T.dir, 3); dynAttr(T.g, 'aDist', T.dist, 1); dynAttr(T.g, 'aInfo', T.info, 3); T.P = { svDir: T.dir, svDist: T.dist, svInfo: T.info };
    const lz = Math.log(1 + DATA.SURV_ZMAX), seed = R.tiles.length * 7919 + 13;
    const dOf = x => { const lut = R.survLut; if (!lut) return 0; const K = lut.length - 1, y = x * K, k = Math.min(y | 0, K - 1); return lut[k] + (lut[k + 1] - lut[k]) * (y - k); };
    T.append = (b, off, cnt) => { for (let k = 0, o = off, i = T.n; k < cnt; k++, o += 6, i++) { const lon = (b[o] | b[o + 1] << 8) / 65535 * TAU, w = b[o + 2] | b[o + 3] << 8, lat = ((w & 32767) / 32767 - 0.5) * Math.PI, zu = (b[o + 4] | b[o + 5] << 8) / 65535, cl = Math.cos(lat), j = i * 3;
        T.dir[j] = cl * Math.cos(lon); T.dir[j + 1] = cl * Math.sin(lon); T.dir[j + 2] = Math.sin(lat); T.zu[i] = zu; T.dist[i] = dOf(zu); T.info[j] = Math.exp(zu * lz) - 1; T.info[j + 1] = (Math.imul(i + seed, 2654435761) >>> 0) / 4294967296; T.info[j + 2] = (w >> 15) ? 2 : 1; }
      T.n += cnt; };
    T.redist = () => { for (let i = 0; i < T.n; i++) T.dist[i] = dOf(T.zu[i]); T.full = true; };
    return tileObj(T, SH.surv, 2); };
  { const base = R.setSurvey; R.setSurvey = lut => { R.survLut = lut; base(lut); for (const T of R.tiles) if (T.kind === 'gal') T.redist(); }; }
  const flushTile = T => {       // n'envoie à la carte graphique que les objets arrivés depuis la dernière image
    if (T.full) { for (const [nm] of T.attrs) { const a = T.g.attributes[nm]; a.updateRange.offset = 0; a.updateRange.count = -1; a.needsUpdate = true; } T.full = false; T.sent = T.n; }
    else if (T.n > T.sent) { for (const [nm, sz] of T.attrs) { const a = T.g.attributes[nm]; a.updateRange.offset = T.sent * sz; a.updateRange.count = (T.n - T.sent) * sz; a.needsUpdate = true; } T.sent = T.n; } };
  // --- cellules : une fois un morceau d'étoiles reçu en entier, il est réparti en blocs compacts de l'espace, chacun trié par éclat.
  //     À chaque image, on ne dessine que les blocs situés dans le champ de vue et, dans chacun, que les étoiles assez brillantes pour être visibles.
  // --- astéroïdes en flux : la position sur l'orbite (équation de Kepler) est résolue par la carte graphique, pour chaque point, à chaque image
  SH.kep = { v: `attribute vec3 aQ; attribute vec3 aEl; attribute vec2 aLook; uniform float uT,uOpacity,uDpr; uniform vec3 uColor; varying vec3 vColor; varying float vA;
void main(){ float e=aEl.x; float M=mod(aEl.y+aEl.z*uT,6.2831853); float E=M+e*sin(M)*(1.0+e*cos(M)); for(int k=0;k<7;k++){ E-=(E-e*sin(E)-M)/(1.0-e*cos(E)); }
  vec4 mv=modelViewMatrix*vec4(position*(cos(E)-e)+aQ*sin(E),1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0; vA=aLook.y*uOpacity; vColor=uColor; gl_PointSize=clamp(aLook.x*1.5,1.0,4.5)*uDpr; }`, f: FRAG_SOFT };
  R.addAstTile = cap => {
    const T = { kind: 'ast', rec: 28, cap, n: 0, sent: 0, draw: 0, pos: new Float32Array(cap * 3), q: new Float32Array(cap * 3), el: new Float32Array(cap * 3), look: new Float32Array(cap * 2), H: new Float32Array(cap), epoch: DATA.AST_EPOCH, u: { uT: U(0), uOpacity: U(0), uDpr: U(1), uColor: U(new THREE.Color(0.8, 0.75, 0.68)) }, attrs: [['position', 3], ['aQ', 3], ['aEl', 3], ['aLook', 2]], g: new THREE.BufferGeometry() };
    dynAttr(T.g, 'position', T.pos, 3); dynAttr(T.g, 'aQ', T.q, 3); dynAttr(T.g, 'aEl', T.el, 3); dynAttr(T.g, 'aLook', T.look, 2);
    T.append = (b, off, cnt) => { const f = new Float32Array(b.buffer.slice(b.byteOffset + off, b.byteOffset + off + cnt * 28));
      for (let k = 0, i = T.n; k < cnt; k++, i++) { const a = f[k * 7], e = f[k * 7 + 1], inc = f[k * 7 + 2], om = f[k * 7 + 3], w = f[k * 7 + 4], bb = a * Math.sqrt(1 - e * e), co = Math.cos(om), so = Math.sin(om), ci = Math.cos(inc), si = Math.sin(inc), cw = Math.cos(w), sw = Math.sin(w), j = i * 3;
        T.pos[j] = a * (co * cw - so * sw * ci); T.pos[j + 1] = a * (so * cw + co * sw * ci); T.pos[j + 2] = a * sw * si; T.q[j] = bb * (-co * sw - so * cw * ci); T.q[j + 1] = bb * (-so * sw + co * cw * ci); T.q[j + 2] = bb * cw * si;
        T.el[j] = e; T.el[j + 1] = f[k * 7 + 5]; T.el[j + 2] = 0.01720209895 / Math.pow(a, 1.5); T.H[i] = f[k * 7 + 6]; T.look[i * 2] = clamp(2.1 - (f[k * 7 + 6] - 11) * 0.28, 0.75, 2.1); T.look[i * 2 + 1] = 0.55; }
      T.n += cnt; };
    return tileObj(T, SH.kep, 44); };
  // Les cellules sont des secteurs du ciel vus depuis le Soleil (6 faces d'un cube, chacune en 6 × 6), coupés en une partie proche et une partie lointaine.
  // Quand la caméra est près du Soleil, ce qui est le cas le plus fréquent, tout secteur hors du champ de vue est écarté d'un seul test.
  const NG = 6, NCELL = 6 * NG * NG * 2, FRU = new THREE.Frustum(), PMX = new THREE.Matrix4(); R.mcut = 13.2;
  R.buildCells = async (T, pause) => {
    const n = T.n, pos = T.pos, mag = T.mag, key = new Uint16Array(n), cnt = new Uint32Array(NCELL + 1), smp = [];
    for (let i = 0, st = Math.max(1, Math.floor(n / 20000)); i < n; i += st) smp.push(pos[i * 3] * pos[i * 3] + pos[i * 3 + 1] * pos[i * 3 + 1] + pos[i * 3 + 2] * pos[i * 3 + 2]);
    smp.sort((a, b) => a - b); const d2med = smp[smp.length >> 1] || 0;
    for (let i = 0; i < n; i++) { const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2], ax = Math.abs(x), ay = Math.abs(y), az = Math.abs(z); let f, u, v;
      if (ax >= ay && ax >= az) { const m = ax || 1e-9; f = x < 0 ? 1 : 0; u = y / m; v = z / m; } else if (ay >= az) { f = y < 0 ? 3 : 2; u = x / ay; v = z / ay; } else { f = z < 0 ? 5 : 4; u = x / az; v = y / az; }
      const iu = Math.min(NG - 1, ((u + 1) * 0.5 * NG) | 0), iv = Math.min(NG - 1, ((v + 1) * 0.5 * NG) | 0), k = ((f * NG + iu) * NG + iv) * 2 + (x * x + y * y + z * z > d2med ? 1 : 0); key[i] = k; cnt[k + 1]++;
      if ((i & 262143) === 262143) await pause(); }
    for (let k = 0; k < NCELL; k++) cnt[k + 1] += cnt[k];
    const idx = new Uint32Array(n), fill = cnt.slice(0, NCELL), leaves = []; for (let i = 0; i < n; i++) idx[fill[key[i]]++] = i;
    for (let k = 0; k < NCELL; k++) { const a = cnt[k], b = cnt[k + 1]; if (b <= a) continue;
      idx.set(Array.from(idx.subarray(a, b)).sort((p, q) => mag[p] - mag[q]), a);        // dans chaque cellule : de la plus brillante à la plus faible
      let x0 = 1e30, x1 = -1e30, y0 = 1e30, y1 = -1e30, z0 = 1e30, z1 = -1e30;
      for (let q = a; q < b; q++) { const j = idx[q] * 3, x = pos[j], y = pos[j + 1], z = pos[j + 2]; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; if (z < z0) z0 = z; if (z > z1) z1 = z; }
      let sx = 0, sy = 0, sz = 0, rmin = 1e30, rmax = 0; for (let q = a; q < b; q++) { const j = idx[q] * 3, x = pos[j], y = pos[j + 1], z = pos[j + 2], d = Math.hypot(x, y, z) || 1e-9; sx += x / d; sy += y / d; sz += z / d; if (d < rmin) rmin = d; if (d > rmax) rmax = d; }
      const sn = Math.hypot(sx, sy, sz) || 1; sx /= sn; sy /= sn; sz /= sn; let cmin = 1; for (let q = a; q < b; q++) { const j = idx[q] * 3, x = pos[j], y = pos[j + 1], z = pos[j + 2], c = (x * sx + y * sy + z * sz) / (Math.hypot(x, y, z) || 1e-9); if (c < cmin) cmin = c; }
      leaves.push({ a, n: b - a, lo: [x0, y0, z0], hi: [x1, y1, z1], dir: [sx, sy, sz], ang: Math.acos(clamp(cmin, -1, 1)), rmin, rmax, dc: 0 }); if (k % 16 === 15) await pause(); }
    const p2 = new Float32Array(n * 3), m2 = new Float32Array(n), c2 = new Uint8Array(n), v2 = new Int8Array(n * 3), k2 = new Uint8Array(n * 3);
    for (let i = 0; i < n; i++) { const q = idx[i], j = q * 3, o = i * 3; p2[o] = pos[j]; p2[o + 1] = pos[j + 1]; p2[o + 2] = pos[j + 2]; m2[i] = mag[q]; c2[i] = T.ci[q]; v2[o] = T.vel[j]; v2[o + 1] = T.vel[j + 1]; v2[o + 2] = T.vel[j + 2]; k2[o] = T.col[j]; k2[o + 1] = T.col[j + 1]; k2[o + 2] = T.col[j + 2]; }
    T.pos.set(p2); T.mag.set(m2); T.ci.set(c2); T.vel.set(v2); T.col.set(k2); T.full = true;
    const grp = new THREE.Group(); grp.visible = false; scene.add(grp);
    for (const L of leaves) { const g = new THREE.BufferGeometry(); for (const [nm] of T.attrs) g.setAttribute(nm, T.g.attributes[nm]); g.setDrawRange(L.a, 0); const o = new THREE.Points(g, T.obj.material); o.frustumCulled = false; o.renderOrder = 8; o.visible = false; grp.add(o); L.o = o; L.g = g; }
    scene.remove(T.obj); T.leaves = leaves; T.grp = grp;
  };
  const cellPass = (T, F, unitToPc, expo) => {
    const s = F.s * LY, ox = -F.tg[0] * F.s, oy = -F.tg[1] * F.s, oz = -F.tg[2] * F.s, cam = camera.position, infl = Math.min(Math.abs(F.ty) * 0.00085, 5000), mag = T.mag, pl = FRU.planes, cut = T.u.uMcut.value + expo;
    const dcam = Math.hypot(cam.x - ox, cam.y - oy, cam.z - oz) / s, k0 = [0, 0, 0, 0]; for (let p = 0; p < 4; p++) k0[p] = pl[p].normal.x * ox + pl[p].normal.y * oy + pl[p].normal.z * oz + pl[p].constant;      // distance du Soleil à chaque bord du champ de vue
    let drawn = 0, cells = 0, head = null, hs = 0, hc = 0;
    const flush = () => { if (head) { head.o.visible = true; head.g.setDrawRange(hs, hc); cells++; head = null; } };
    for (const L of T.leaves) { L.o.visible = false; const rmin = Math.max(L.rmin - infl, 0), rmax = L.rmax + infl, ang = L.ang + (infl > 0 ? Math.asin(Math.min(1, infl / Math.max(L.rmin, 1e-9))) : 0), ca = Math.cos(Math.min(ang, Math.PI)), sa = Math.sin(Math.min(ang, Math.PI)); let vis = true;
      if (ang < Math.PI) for (let p = 0; p < 4; p++) { const q = pl[p], c = q.normal.x * L.dir[0] + q.normal.y * L.dir[1] + q.normal.z * L.dir[2], md = c >= ca ? 1 : c * ca + Math.sqrt(Math.max(1 - c * c, 0)) * sa;       // plus grande composante, le long de la normale, d'une direction du cône
        if (md * (md < 0 ? rmin : rmax) * s + k0[p] < 0) { vis = false; break; } }
      if (vis) { const x0 = (L.lo[0] - infl) * s + ox, x1 = (L.hi[0] + infl) * s + ox, y0 = (L.lo[1] - infl) * s + oy, y1 = (L.hi[1] + infl) * s + oy, z0 = (L.lo[2] - infl) * s + oz, z1 = (L.hi[2] + infl) * s + oz;
        const dx = Math.max(x0 - cam.x, 0, cam.x - x1), dy = Math.max(y0 - cam.y, 0, cam.y - y1), dz = Math.max(z0 - cam.z, 0, cam.z - z1), dmin = Math.max(Math.hypot(dx, dy, dz) / s, rmin - dcam, dcam - rmax, 0) * s * unitToPc, Mlim = cut - 5 * Math.log10(Math.max(dmin, 1e-4) / 10);
        let lo = L.a, hi = L.a + L.n; while (lo < hi) { const m = (lo + hi) >> 1; if (mag[m] <= Mlim) lo = m + 1; else hi = m; } L.dc = lo - L.a; } else L.dc = 0;
      if (L.dc > 0) { drawn += L.dc; if (head && hs + hc === L.a) hc += L.dc; else { flush(); head = L; hs = L.a; hc = L.dc; } if (L.dc < L.n) flush(); }      // cellules voisines entièrement dessinées : un seul appel de dessin
      else flush(); }
    flush(); T.drawn = drawn; T.cellsOn = cells; };
  const sunStarU = starU();
  const sunStar = pts({ position: [new Float32Array(3), 3], aMag: [new Float32Array([4.83]), 1], aCol: [new Float32Array(bvToRgb(0.656)), 3] }, mk(SH.star, sunStarU), 9);
  // petits corps (UA)
  const dotsU = c => ({ uOpacity: U(1), uDpr: U(1), uZ: U(1), uColor: U(new THREE.Color(c[0], c[1], c[2])) });
  const oortU = dotsU([0.5, 0.62, 0.8]);
  const oort = pts({ position: [G.oort.pos, 3], aLook: [G.oort.look, 2] }, mk(SH.dots, oortU), 10); R.oortDirty = () => { oort.geometry.attributes.position.needsUpdate = true; oort.geometry.attributes.aLook.needsUpdate = true; };
  const beltU = dotsU([0.74, 0.66, 0.56]), kuiperU = dotsU([0.56, 0.66, 0.8]);
  beltU.uZ.value = 0; kuiperU.uZ.value = 0;
  const AST = decodeBodies('AST'), TNO = decodeBodies('TNO'); R.AST = AST; R.TNO = TNO;
  AST.count = Math.round(AST.N * (Q.bodies || 1)); TNO.count = Math.round(TNO.N * (Q.bodies || 1));
  const belt = pts({ position: [AST.pos, 3], aLook: [AST.look, 2] }, mk(SH.dots, beltU, { depthTest: true }), 45); belt.geometry.setDrawRange(0, AST.count);
  const kuiper = pts({ position: [TNO.pos, 3], aLook: [TNO.look, 2] }, mk(SH.dots, kuiperU, { depthTest: true }), 45); kuiper.geometry.setDrawRange(0, TNO.count);
  // comètes (JPL), étoiles à planètes connues, pulsars : positions réelles
  const COM = decodeComets(); R.COM = COM; const cometU = dotsU([0.6, 0.92, 1.0]), comets = pts({ position: [COM.pos, 3], aLook: [COM.look, 2] }, mk(SH.dots, cometU, { depthTest: true }), 46);
  const fpos = k => new Float32Array(b64ToBytes(DATA[k]).buffer), mkLook = (n, s, a) => { const l = new Float32Array(n * 2); for (let i = 0; i < n; i++) { l[i * 2] = s; l[i * 2 + 1] = a; } return l; };
  R.EXO = { N: DATA.EXO_N, pos: fpos('EXO_POS') }; R.PSR = { N: DATA.PSR_N, pos: fpos('PSR_POS') };
  const exoU = dotsU([0.42, 1.0, 0.6]), exo = pts({ position: [R.EXO.pos, 3], aLook: [mkLook(R.EXO.N, 1.9, 0.85), 2] }, mk(SH.dots, exoU), 9);
  const psrU = dotsU([0.8, 0.62, 1.0]), psr = pts({ position: [R.PSR.pos, 3], aLook: [mkLook(R.PSR.N, 1.9, 0.85), 2] }, mk(SH.dots, psrU), 9);
  // trous noirs : stellaires dans la Voie lactée (années-lumière), supermassifs au centre d'autres galaxies (Mpc)
  const f32 = s => new Float32Array(b64ToBytes(s).buffer);
  R.BHS = { N: DATA.BHS.n, pos: f32(DATA.BHS.pos) }; R.BHM = { N: DATA.BHM.n, pos: new Float32Array(DATA.BHM.n * 3) };
  { const d = f32(DATA.BHM.dir), k = f32(DATA.BHM.dist); for (let i = 0; i < R.BHM.N; i++) { R.BHM.pos[i * 3] = d[i * 3] * k[i]; R.BHM.pos[i * 3 + 1] = d[i * 3 + 1] * k[i]; R.BHM.pos[i * 3 + 2] = d[i * 3 + 2] * k[i]; } }
  const bhsU = dotsU([1.0, 0.5, 0.16]), bhs = pts({ position: [R.BHS.pos, 3], aLook: [mkLook(R.BHS.N, 2.7, 1), 2] }, mk(SH.dots, bhsU), 9);
  const bhmU = dotsU([1.0, 0.5, 0.16]), bhm = pts({ position: [R.BHM.pos, 3], aLook: [mkLook(R.BHM.N, 2.5, 1), 2] }, mk(SH.dots, bhmU), 9); R.bhmDirty = () => { bhm.geometry.attributes.position.needsUpdate = true; };
  // orbite de l'objet sélectionné (astéroïde, objet lointain, comète) : ellipse complète autour du Soleil
  const selLineG = new THREE.BufferGeometry(); selLineG.setAttribute('position', new THREE.BufferAttribute(new Float32Array(257 * 3), 3));
  const selLine = new THREE.Group(), selOff = [];       // le même tracé dessiné quatre fois, décalé de moins d'un pixel : un trait plus épais
  for (const d of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const u = { uColor: U(new THREE.Color(1.0, 0.8, 0.42)), uOpacity: U(0.6), uOff: U(new THREE.Vector2()) };
    const l = new THREE.Line(selLineG, new THREE.ShaderMaterial(Object.assign({ vertexShader: 'uniform vec2 uOff; void main(){ gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); gl_Position.xy+=uOff*gl_Position.w; gl_Position.z=0.0; }', fragmentShader: 'uniform vec3 uColor; uniform float uOpacity; void main(){ gl_FragColor=vec4(uColor*uOpacity*1.5,uOpacity); }', uniforms: u }, additive)));
    l.frustumCulled = false; l.renderOrder = 47; selLine.add(l); selOff.push([u, d]); }
  selLine.visible = false; scene.add(selLine); let selOrb = null;
  // lunes : un petit groupe de points par planète, en positions relatives à la planète
  const moonSets = {}; R.initMoons = sets => { for (const s of sets) { const u = dotsU(s.col || [0.86, 0.9, 1.0]), o = pts({ position: [s.rel, 3], aLook: [s.look, 2] }, mk(SH.dots, u), 48); moonSets[s.key] = { o, u, s }; } }; R.moonVis = 0;
  // figures des constellations : segments entre étoiles réelles
  let cons = null, consU = null; R.constVis = 0;
  R.initConst = pos => { consU = { uColor: U(new THREE.Color(0.36, 0.5, 0.92)), uOpacity: U(0) }; const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    cons = new THREE.LineSegments(g, new THREE.ShaderMaterial(Object.assign({ vertexShader: 'void main(){ gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); gl_Position.z=0.0; }', fragmentShader: 'uniform vec3 uColor; uniform float uOpacity; void main(){ gl_FragColor=vec4(uColor*uOpacity,uOpacity); }', uniforms: consU }, additive)));
    cons.frustumCulled = false; cons.renderOrder = 7; cons.visible = false; scene.add(cons); };
  R.setSelOrbit = o => { selOrb = o; if (!o) return; const a = selLineG.attributes.position.array; if (o.pts) a.set(o.pts); else for (let k = 0; k <= 256; k++) { const E = k / 256 * TAU, x = Math.cos(E) - o.e, y = Math.sin(E); a[k * 3] = o.P[0] * x + o.Q[0] * y; a[k * 3 + 1] = o.P[1] * x + o.Q[1] * y; a[k * 3 + 2] = o.P[2] * x + o.Q[2] * y; } selLineG.attributes.position.needsUpdate = true; };

  /* ---- fond diffus cosmologique et cercles d'horizon ---- */
  const cmbU = { uOpacity: U(1), uMap: U(new THREE.TextureLoader().load(DATA.CMB)) }; cmbU.uMap.value.wrapS = THREE.RepeatWrapping;
  const cmb = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 40), new THREE.ShaderMaterial(Object.assign({ vertexShader: SH.cmb.v, fragmentShader: SH.cmb.f, uniforms: cmbU }, additive, { side: THREE.BackSide })));
  cmb.frustumCulled = false; cmb.renderOrder = 0; scene.add(cmb);
  { const X = new THREE.Vector3(M[0][0], M[1][0], M[2][0]), Y = new THREE.Vector3(M[0][2], M[1][2], M[2][2]); cmb.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(X, Y, new THREE.Vector3().crossVectors(X, Y))); }   // carte en coordonnées galactiques
  const quad = new THREE.PlaneGeometry(2, 2);
  const mkHalo = (c) => { c = c || [0.38, 0.27, 1.0]; const u = { uRad: U(1), uColor: U(new THREE.Color(c[0], c[1], c[2])), uOpacity: U(0) }; const m = new THREE.Mesh(quad, new THREE.ShaderMaterial(Object.assign({ vertexShader: SH.glow.v, fragmentShader: SH.halo.f, uniforms: u }, additive))); m.frustumCulled = false; m.renderOrder = 4; m.userData.u = u; scene.add(m); return m; };
  const halos = [[mkHalo(), null], [mkHalo(), G.lg.m31.c]], cores = [[mkHalo([1.0, 0.8, 0.58]), null], [mkHalo([1.0, 0.8, 0.58]), G.lg.m31.c]];
  // --- système planétaire d'une étoile : orbites de toutes ses planètes, et halo de l'étoile au centre
  const LINE_V = 'void main(){ gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); gl_Position.z=0.0; }', LINE_F = 'uniform vec3 uColor; uniform float uOpacity; void main(){ gl_FragColor=vec4(uColor*uOpacity,uOpacity); }';
  const sysG = new THREE.BufferGeometry(), sysPos = new Float32Array(10 * 128 * 2 * 3); sysG.setAttribute('position', new THREE.BufferAttribute(sysPos, 3)); sysG.setDrawRange(0, 0);
  const sysU = { uColor: U(new THREE.Color(0.5, 0.72, 1.0)), uOpacity: U(0) }, sysLines = new THREE.LineSegments(sysG, new THREE.ShaderMaterial(Object.assign({ vertexShader: LINE_V, fragmentShader: LINE_F, uniforms: sysU }, additive)));
  sysLines.frustumCulled = false; sysLines.renderOrder = 46; sysLines.visible = false; scene.add(sysLines); const sysStar = mkHalo([1.0, 0.9, 0.72]); let sysOn = false;
  // étoile vue de près : un disque à sa taille réelle, assombri au bord, entouré d'une lueur ; placé par le processeur, donc sans tremblement
  SH.sdisc = { f: `uniform vec3 uColor; uniform float uOpacity,uDisc; varying vec2 vUv; void main(){ float r=length(vUv); if(r>1.0) discard; vec3 c;
    if(r<uDisc){ float mu=sqrt(max(1.0-(r/uDisc)*(r/uDisc),0.0)); c=mix(uColor,vec3(1.0),0.18)*(0.36+0.64*mu)*1.12; } else { float g=(r-uDisc)/(1.0-uDisc); c=uColor*(0.5+1.9*step(uDisc,0.02))*pow(1.0-g,3.0)/(1.0+8.0*g); }
    gl_FragColor=vec4(c*uOpacity,1.0); }` };
  const nearPool = []; for (let k = 0; k < 8; k++) { const u = { uRad: U(1), uColor: U(new THREE.Color(1, 1, 1)), uOpacity: U(0), uDisc: U(0.01) }, m = new THREE.Mesh(quad, new THREE.ShaderMaterial(Object.assign({ vertexShader: SH.glow.v, fragmentShader: SH.sdisc.f, uniforms: u }, additive))); m.frustumCulled = false; m.renderOrder = 9; m.visible = false; scene.add(m); nearPool.push([m, u]); }
  R.setSysOrbits = L => { sysOn = !!(L && L.length); let k = 0; if (L) for (const o of L.slice(0, 10)) for (let j = 0; j < 128; j++) for (const E of [j / 128 * TAU, (j + 1) / 128 * TAU]) { const x = Math.cos(E) - o.e, y = Math.sin(E); sysPos[k++] = o.P[0] * x + o.Q[0] * y; sysPos[k++] = o.P[1] * x + o.Q[1] * y; sysPos[k++] = o.P[2] * x + o.Q[2] * y; } sysG.setDrawRange(0, k / 3); sysG.attributes.position.needsUpdate = true; };
  R.moonLookDirty = key => { if (moonSets[key]) moonSets[key].o.geometry.attributes.aLook.needsUpdate = true; };
  R.azelFrom = (d, mix) => { const q = qI.clone().slerp(qFrameGal, mix).invert(), v = new THREE.Vector3(d[0], d[1], d[2]).applyQuaternion(q); return [Math.atan2(v.y, v.x), Math.asin(clamp(v.z, -1, 1))]; };      // d'où regarder pour voir un objet tel qu'on le voit depuis le Soleil
  // --- photos réelles de galaxies : des vignettes rangées dans de grandes images, posées à plat dans l'espace, face au Soleil, nord en haut
  SH.photo = { v: `uniform vec3 uC,uE,uN; varying vec2 vUv; void main(){ vUv=uv; vec3 p=uC+uE*(1.0-2.0*uv.x)+uN*(2.0*uv.y-1.0); gl_Position=projectionMatrix*viewMatrix*vec4(p,1.0); gl_Position.z=0.0; }`,
    f: `uniform sampler2D uTex; uniform vec4 uCell; uniform float uOpacity,uFloor; varying vec2 vUv; void main(){ vec2 q=vUv*2.0-1.0; float r=length(q); if(r>1.0) discard; vec3 c=texture2D(uTex,uCell.xy+(vUv*0.98+0.01)*uCell.zw).rgb; c=pow(max(c-uFloor,0.0)/(1.0-uFloor),vec3(1.2)); gl_FragColor=vec4(c*(1.0-smoothstep(0.7,1.0,r))*uOpacity,1.0); }` };
  const phQuad = new THREE.PlaneGeometry(1, 1), phPool = [], phTex = [];
  for (let k = 0; k < 14; k++) { const u = { uC: U(new THREE.Vector3()), uE: U(new THREE.Vector3()), uN: U(new THREE.Vector3()), uTex: U(null), uCell: U(new THREE.Vector4()), uOpacity: U(0), uFloor: U(0.06) }, m = new THREE.Mesh(phQuad, new THREE.ShaderMaterial(Object.assign({ vertexShader: SH.photo.v, fragmentShader: SH.photo.f, uniforms: u, side: THREE.DoubleSide }, additive))); m.frustumCulled = false; m.renderOrder = 5; m.visible = false; scene.add(m); phPool.push([m, u]); }
  R.loadPhotos = urls => urls.forEach((url, i) => { new THREE.TextureLoader().load(url, t => { t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter; t.generateMipmaps = false; phTex[i] = t; }); });
  R.photoReady = i => !!phTex[i];
  // --- galaxies en volume. Chaque photo réelle est dépliée en nuage de points : dans le plan du ciel, tout vient de la photo (forme, bras, couleurs) ;
  //     la profondeur est reconstruite selon le type : disque mince incliné remis à plat, sphéroïde, ou nuage épais pour les irrégulières.
  //     Ce qu'une photo ne dit pas reste supposé : l'épaisseur, et lequel des deux bords du disque est le plus proche de nous.
  SH.gvol = { v: `attribute vec3 aCol; attribute float aSz; uniform float uPx,uOpacity,uMinPx,uMaxPx; varying vec3 vColor; varying float vA;
void main(){ vec4 mv=modelViewMatrix*vec4(position,1.0); gl_Position=projectionMatrix*mv; gl_Position.z=0.0; float px=aSz*uPx/max(-mv.z,1e-6); float s=clamp(px,uMinPx,uMaxPx); vColor=aCol; vA=uOpacity*min(1.0,(px*px)/(s*s)); gl_PointSize=s; }`, f: FRAG_SOFT };
  const gvCache = new Map(); let gvBusy = 0, gvTick = 0;
  function gvBuild(p) { const img = phTex[p.atlas] && phTex[p.atlas].image, g3 = p.g3; if (!img || !g3) return null;
    const TW = img.width || 2048, cw = Math.round(p.uv[2] * TW), cv = document.createElement('canvas'); cv.width = cv.height = cw; const cx2 = cv.getContext('2d'); let d;
    try { cx2.drawImage(img, Math.round(p.uv[0] * TW), Math.round((1 - p.uv[1] - p.uv[2]) * TW), cw, cw, 0, 0, cw, cw); d = cx2.getImageData(0, 0, cw, cw).data; } catch (err) { return null; }
    const n2 = cw * cw, I = new Float32Array(n2), med = new Float32Array(n2), h = cw / 2, fl = Math.max(p.floor, g3[6] || 0), kk = cw > 150 ? 4 : 2, st = kk > 2 ? 2 : 1, buf = [];
    for (let i = 0; i < n2; i++) I[i] = Math.max((0.3 * d[i * 4] + 0.5 * d[i * 4 + 1] + 0.2 * d[i * 4 + 2]) / 255 - fl, 0);
    for (let y = 0; y < cw; y++) for (let x = 0; x < cw; x++) { buf.length = 0; for (let b = -kk; b <= kk; b += st) for (let a = -kk; a <= kk; a += st) { const xx = x + a, yy = y + b; if (xx >= 0 && yy >= 0 && xx < cw && yy < cw) buf.push(I[yy * cw + xx]); } buf.sort((u, v) => u - v); med[y * cw + x] = buf[buf.length >> 1]; }
    const c0x = h + g3[4] * h, c0y = h + g3[5] * h; let sum = 0, peak = 0;
    for (let y = 0; y < cw; y++) for (let x = 0; x < cw; x++) { const i = y * cw + x; let v = I[i]; if (Math.hypot(x + 0.5 - c0x, y + 0.5 - c0y) > 0.1 * h && v > 2.2 * med[i] + 0.06) v = med[i];      // étoiles d'avant-plan écrêtées
      v *= 1 - smoothstep(0.8, 0.96, Math.hypot(x + 0.5 - h, y + 0.5 - h) / h); v = v * v / (v + 0.05); I[i] = v; sum += Math.pow(v, 0.72); if (v > peak) peak = v; }
    if (!(sum > 0)) return null;
    const ty0 = g3[3], tier = p.tier || 0, NT = (cw > 150 ? [26000, 60000, 120000] : [8000, 14000, 24000])[tier] * (ty0 === 'S' ? 1.5 : 1), K = NT / sum, nPk = Math.min(Math.pow(peak, 0.72) * K, 12), kpc = p.half / KPC, s = 2 * kpc / cw, Rm = 0.95 * kpc;
    const pa = g3[0] * DEG, cp = Math.cos(pa), sp = Math.sin(pa), ty = g3[3], q = clamp(g3[1], 0.25, 1), inc = clamp(g3[2], 0, 88) * DEG, ci = Math.cos(inc), si = Math.sin(inc), edgeW = ty === 'D' ? smoothstep(66 * DEG, 80 * DEG, inc) : 0;
    const E = p.e, Nn = p.n, Lv = p.l, mA = [cp * Nn[0] + sp * E[0], cp * Nn[1] + sp * E[1], cp * Nn[2] + sp * E[2]], pA = [cp * E[0] - sp * Nn[0], cp * E[1] - sp * Nn[1], cp * E[2] - sp * Nn[2]];
    const vA = [ci * pA[0] + si * Lv[0], ci * pA[1] + si * Lv[1], ci * pA[2] + si * Lv[2]], hA = [-ci * Lv[0] + si * pA[0], -ci * Lv[1] + si * pA[1], -ci * Lv[2] + si * pA[2]];
    let seed = (p.id * 2654435761 + 12345) >>> 0; const rnd = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    const pos = [], col = [], sz = [];
    for (let y = 0; y < cw; y++) for (let x = 0; x < cw; x++) { const i = y * cw + x, want = Math.min(Math.pow(I[i], 0.72) * K, 12), wI = Math.pow(I[i] / peak, 0.28); let n = Math.floor(want); if (rnd() < want - n) n++; if (!n) continue;
      let cr = d[i * 4] / 255 - fl, cg = d[i * 4 + 1] / 255 - fl, cb = d[i * 4 + 2] / 255 - fl; const mx = Math.max(cr, cg, cb, 1e-3), lum = (cr + cg + cb) / 3 / mx; cr = clamp(lum + (cr / mx - lum) * 1.35, 0.05, 1); cg = clamp(lum + (cg / mx - lum) * 1.35, 0.05, 1); cb = clamp(lum + (cb / mx - lum) * 1.35, 0.05, 1);
      for (let j = 0; j < n; j++) { const xi = -(x + rnd() - c0x) * s, eta = -(y + rnd() - c0y) * s, x1 = xi * sp + eta * cp, y1 = xi * cp - eta * sp; let wx, wy, wz, rg;
        if (ty === 'D') { let yg, z; if (rnd() < edgeW) { z = y1 / Math.max(si, 0.5); const Lh = Math.sqrt(Math.max(Rm * Rm - x1 * x1, 0)); yg = (rnd() + rnd() + rnd() - 1.5) / 1.5 * Lh * 0.75; } else { yg = y1 / Math.max(ci, 0.34); const u = 0.03 + 0.94 * rnd(); z = 0.022 * Rm * Math.log(u / (1 - u)); const rb = Math.hypot(x1, yg) / (0.13 * Rm); if (rb < 1) z *= 1 + 4 * (1 - rb); }
          rg = Math.hypot(x1, yg); wx = x1 * mA[0] + yg * vA[0] + z * hA[0]; wy = x1 * mA[1] + yg * vA[1] + z * hA[1]; wz = x1 * mA[2] + yg * vA[2] + z * hA[2]; }
        else { let dep; if (ty === 'S') { const m2 = x1 * x1 + y1 * y1 / (q * q) + 0.0009 * Rm * Rm, sm = Math.sqrt(Math.max(Rm * Rm - x1 * x1 - y1 * y1, 0)), tm = sm / Math.sqrt(sm * sm + m2), t = (2 * rnd() - 1) * tm; dep = Math.sqrt(m2) * t / Math.sqrt(Math.max(1 - t * t, 1e-6)); } else dep = (rnd() + rnd() + rnd() - 1.5) * (0.45 * Math.hypot(x1, y1) + 0.04 * Rm);
          rg = Math.hypot(x1, y1); wx = x1 * mA[0] + y1 * pA[0] + dep * Lv[0]; wy = x1 * mA[1] + y1 * pA[1] + dep * Lv[1]; wz = x1 * mA[2] + y1 * pA[2] + dep * Lv[2]; }
        pos.push(wx, wy, wz); const w = (0.75 + 0.25 * rnd()) * wI;
        if (p.gray) { const t = ty === 'S' ? 0 : smoothstep(0.06, 0.55, rg / Rm), g = cr; col.push(g * lerp(1.0, 0.74, t) * w, g * lerp(0.87, 0.85, t) * w, g * lerp(0.68, 1.0, t) * w); } else col.push(cr * w, cg * w, cb * w);      // photo en noir et blanc : teinte supposée, chaude au cœur, bleutée dans le disque
        sz.push(s * (ty === 'S' ? 3.4 : ty === 'I' ? 2.2 : 1.6)); } }
    const n = sz.length; if (!n) return null; const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3)); geo.setAttribute('aCol', new THREE.BufferAttribute(new Float32Array(col), 3)); geo.setAttribute('aSz', new THREE.BufferAttribute(new Float32Array(sz), 1));
    const u = { uPx: U(1), uOpacity: U(0), uMinPx: U(1.5), uMaxPx: U(64) }, pts = new THREE.Points(geo, new THREE.ShaderMaterial(Object.assign({ vertexShader: SH.gvol.v, fragmentShader: SH.gvol.f, uniforms: u }, additive))); pts.frustumCulled = false; pts.renderOrder = 6; pts.visible = false; scene.add(pts);
    const ce = Math.max(ci, 0.34);      // plan du disque : la photo y est remise à plat (voir le dessin plus bas)
    return { pts, u, n, a0: 0.9 / Math.max(nPk, 1) / (ty === 'S' ? 3.2 : ty === 'I' ? 1.6 : 1), used: 0, ty, edgeW, L: Lv, A: [sp * mA[0] + cp / ce * vA[0], sp * mA[1] + cp / ce * vA[1], sp * mA[2] + cp / ce * vA[2]], B: [cp * mA[0] - sp / ce * vA[0], cp * mA[1] - sp / ce * vA[1], cp * mA[2] - sp / ce * vA[2]] }; }
  function gvGet(p) { let M = gvCache.get(p.id); if (M === undefined && gvBusy < 1 && p.op > 0.04) { gvBusy++; M = gvBuild(p) || false; gvCache.set(p.id, M);
      if (gvCache.size > 7) { let old = null, ok = null; gvCache.forEach((v, k) => { if (v && k !== p.id && (!old || v.used < old.used)) { old = v; ok = k; } }); if (old) { scene.remove(old.pts); old.pts.geometry.dispose(); old.pts.material.dispose(); gvCache.delete(ok); } } }
    return M || null; }
  function gvDraw(M, p, F, dpr) { M.used = ++gvTick; M.pts.visible = true; place(M.pts, p.c, KPC, F); const cvs = renderer.domElement; M.u.uPx.value = cvs.height * 0.5 / Math.tan(FOV * DEG / 2) * KPC * F.s; M.u.uOpacity.value = M.a0 * p.op * (M.ty === 'D' ? lerp(0.5, 1, M.edgeW) : 0.7); M.u.uMinPx.value = 1.6 * dpr; M.u.uMaxPx.value = 72 * dpr; }
  R.galVolumes = () => gvCache.size;
  // --- lueur du jeune univers : avant et juste après que l'univers devienne transparent, tout le ciel rougeoie
  const egU = { uColor: U(new THREE.Color(0, 0, 0)) }, egQ = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial(Object.assign({ vertexShader: 'void main(){ gl_Position=vec4(position.xy,0.0,1.0); }', fragmentShader: 'uniform vec3 uColor; void main(){ gl_FragColor=vec4(uColor,1.0); }', uniforms: egU }, additive)));
  egQ.frustumCulled = false; egQ.renderOrder = -9; egQ.visible = false; scene.add(egQ);
  // --- axes des ombres de la Lune et de la Terre : quand l'un touche l'autre astre, il y a éclipse
  const sxG = new THREE.BufferGeometry(), sxP = new Float32Array(12); sxG.setAttribute('position', new THREE.BufferAttribute(sxP, 3));
  const sxU = { uColor: U(new THREE.Color(0.62, 0.68, 0.8)), uOpacity: U(0) }, sxL = new THREE.LineSegments(sxG, new THREE.ShaderMaterial(Object.assign({ vertexShader: 'void main(){ gl_Position=projectionMatrix*viewMatrix*vec4(position,1.0); gl_Position.z=0.0; }', fragmentShader: LINE_F, uniforms: sxU }, additive)));
  sxL.frustumCulled = false; sxL.renderOrder = 47; sxL.visible = false; scene.add(sxL);
  // --- fond de ciel : panorama réel de la Voie lactée (ESO/S. Brunier), vu depuis le voisinage du Soleil. Il donne la lueur diffuse que les étoiles du catalogue, une à une, ne rendent pas.
  const skyU = { uMap: U(null), uGain: U(0), uM: U(new THREE.Matrix3()) }; let skyReady = false;
  { const e = 23.4392911 * DEG, c = Math.cos(e), s = Math.sin(e), G = [[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132], [0.4941094278755837, -0.4448296299600112, 0.7469822444972189], [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]];
    const row = g => [g[0], g[1] * c + g[2] * s, -g[1] * s + g[2] * c], a = row(G[0]), b = row(G[1]), d = row(G[2]); skyU.uM.value.set(a[0], a[1], a[2], b[0], b[1], b[2], d[0], d[1], d[2]);      // galactique ← écliptique
    if (DATA.SKY) new THREE.TextureLoader().load(DATA.SKY, t => { t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter; t.generateMipmaps = false; t.wrapS = THREE.RepeatWrapping; skyU.uMap.value = t; skyReady = true; }); }
  const skyMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 24), new THREE.ShaderMaterial(Object.assign({ vertexShader: 'varying vec3 vD; void main(){ vD=position; gl_Position=projectionMatrix*viewMatrix*vec4(cameraPosition+position*5.0,1.0); gl_Position.z=0.0; }',
    fragmentShader: 'uniform sampler2D uMap; uniform float uGain; uniform mat3 uM; varying vec3 vD; void main(){ vec3 g=uM*normalize(vD); float l=atan(g.y,g.x), b=asin(clamp(g.z,-1.0,1.0)); vec3 c=texture2D(uMap,vec2(0.5-l/6.2831853,0.5+b/3.14159265)).rgb; c=pow(max(c-0.045,0.0),vec3(2.0)); c=mix(vec3(dot(c,vec3(0.3,0.5,0.2))),c,0.78); gl_FragColor=vec4(c*uGain,1.0); }', uniforms: skyU }, additive, { side: THREE.BackSide })));
  skyMesh.frustumCulled = false; skyMesh.renderOrder = -8; skyMesh.visible = false; scene.add(skyMesh);
  const mkRing = (color, dash, order) => { const u = { uRad: U(1), uColor: U(new THREE.Color(color[0], color[1], color[2])), uOpacity: U(1), uWidth: U(0.01), uDash: U(dash) }; const m = new THREE.Mesh(quad, mk(SH.ring, u)); m.frustumCulled = false; m.renderOrder = order; m.userData.u = u; scene.add(m); return m; };
  const rings = { hubble: mkRing([0.61, 0.77, 1.0], 0, 12), event: mkRing([0.95, 0.71, 0.42], 90, 12), particle: mkRing([0.9, 0.92, 0.96], 0, 12), here: mkRing([0.95, 0.71, 0.42], 0, 13), sel: mkRing([1.0, 1.0, 1.0], 0, 50) };

  /* ---- système solaire : orbites, astres ---- */
  const NSEG = 300, oU = new Float32Array((NSEG + 1) * 2), oS = new Float32Array((NSEG + 1) * 2), oI = [];
  for (let i = 0; i <= NSEG; i++) { const u = 0.5 - 0.5 * Math.cos(Math.PI * i / NSEG); oU[i * 2] = oU[i * 2 + 1] = u; oS[i * 2] = -1; oS[i * 2 + 1] = 1; if (i < NSEG) oI.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2); }
  const orbitGeo = new THREE.BufferGeometry();
  orbitGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array((NSEG + 1) * 6), 3)); orbitGeo.setAttribute('aU', new THREE.BufferAttribute(oU, 1)); orbitGeo.setAttribute('aSide', new THREE.BufferAttribute(oS, 1)); orbitGeo.setIndex(oI);
  const orbits = {};
  for (const k of ORBIT_KEYS.concat(['moon'])) {
    const u = { uP: U(new THREE.Vector3()), uQ: U(new THREE.Vector3()), uE0: U(0), uWidth: U(1), uViewport: U(new THREE.Vector2(1, 1)), uColor: U(new THREE.Color(0.52, 0.66, 0.9)), uOpacity: U(1) };
    const m = new THREE.Mesh(orbitGeo, mk(SH.orbit, u, { side: THREE.DoubleSide })); m.frustumCulled = false; m.renderOrder = 20; m.userData.u = u; scene.add(m); orbits[k] = m;
  }
  const sphere = new THREE.SphereGeometry(1, 72, 36), loader = new THREE.TextureLoader(), maxAniso = renderer.capabilities.getMaxAnisotropy();
  const tex = src => { const t = loader.load(src); t.encoding = THREE.sRGBEncoding; t.wrapS = THREE.RepeatWrapping; t.anisotropy = Math.min(4, maxAniso); return t; };
  const bodies = {}, sunWarm = new THREE.Vector3(1.0, 0.72, 0.34);
  for (const b of BODIES) {
    const grp = new THREE.Group(); scene.add(grp);
    let mat, u;
    if (b.key === 'sun') { u = { uGain: U(7), uTime: U(0), uDet: U(1), uColor: U(new THREE.Vector3(1.0, 0.93, 0.82)) }; mat = new THREE.ShaderMaterial({ vertexShader: SH.sun.v, fragmentShader: SH.sun.f, uniforms: u, transparent: true, blending: THREE.NoBlending }); }
    else { u = { uMap: U(tex(DATA.TEX[b.key])), uSun: U(new THREE.Vector3(1, 0, 0)), uAtmo: U(new THREE.Vector3(b.atmo[0], b.atmo[1], b.atmo[2])), uAtmoK: U(b.atmoK), uSpin: U(0), uGain: U(1.25), uOcean: U(b.key === 'earth' ? 1 : 0) }; mat = new THREE.ShaderMaterial({ vertexShader: SH.body.v, fragmentShader: SH.body.f, uniforms: u, transparent: true, blending: THREE.NoBlending }); }
    const mesh = new THREE.Mesh(sphere, mat); mesh.scale.set(1, 1 - b.f, 1); mesh.renderOrder = 40; mesh.frustumCulled = false;
    const spin = new THREE.Group(); spin.add(mesh); grp.add(spin);
    const o = { def: b, grp, spin, mesh, u, pos: [0, 0, 0], px: 0, screen: null, vis: 0 };
    if (b.ring) {
      const rt = loader.load(DATA.TEX.ring); rt.encoding = THREE.sRGBEncoding;
      const ru = { uMap: U(rt), uSun: U(new THREE.Vector3(1, 0, 0)), uCenter: U(new THREE.Vector3()), uNormal: U(new THREE.Vector3(0, 0, 1)), uPlanetR: U(1), uInner: U(b.ring[0]), uOuter: U(b.ring[1]), uGain: U(1.3) };
      const rm = new THREE.Mesh(new THREE.RingGeometry(b.ring[0], b.ring[1], 180, 1), new THREE.ShaderMaterial({ vertexShader: SH.satring.v, fragmentShader: SH.satring.f, uniforms: ru, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor }));
      rm.rotation.x = -Math.PI / 2; rm.renderOrder = 41; rm.frustumCulled = false; spin.add(rm); o.ringU = ru;
    }
    if (b.pole) { const p = [Math.cos(b.pole[1] * DEG) * Math.cos(b.pole[0] * DEG), Math.cos(b.pole[1] * DEG) * Math.sin(b.pole[0] * DEG), Math.sin(b.pole[1] * DEG)], n = [-Math.sin(b.pole[0] * DEG), Math.cos(b.pole[0] * DEG), 0]; o.pole = eqToEcl(p); o.node = eqToEcl(n); o.merid = vcross(o.pole, o.node); }
    bodies[b.key] = o;
  }
  const glowU = { uRad: U(1), uColor: U(new THREE.Color(1.0, 0.86, 0.66)), uOpacity: U(1), uCore: U(40) };
  const glow = new THREE.Mesh(quad, mk(SH.glow, glowU)); glow.frustumCulled = false; glow.renderOrder = 35; scene.add(glow);

  /* ---- post-traitement : accumulation HDR, bloom, courbe de tons ---- */
  const fsScene = new THREE.Scene(), fsCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const fsMat = f => new THREE.ShaderMaterial({ vertexShader: SH.fsv, fragmentShader: f, uniforms: {}, depthTest: false, depthWrite: false });
  const mBright = fsMat(SH.bright), mBlur = fsMat(SH.blur), mFinal = fsMat(SH.final);
  mBright.uniforms = { tMap: U(null), uTexel: U(new THREE.Vector2()), uThresh: U(1.0) };
  mBlur.uniforms = { tMap: U(null), uDir: U(new THREE.Vector2()) };
  mFinal.uniforms = { tMap: U(null), tB1: U(null), tB2: U(null), uBloom: U(1), uExposure: U(1), uTime: U(0), uRes: U(new THREE.Vector2(1, 1)), uLens: U(0), uFlip: U(1), uPsiC: U(0), uCubeOn: U(0), uLl: U(new THREE.Vector2(0, 1)), tCube: U(null), tLut: U(null), uBH: U(new THREE.Vector3(0, 0, -1)), uTanF: U(new THREE.Vector2(1, 1)), uRot: U(new THREE.Matrix3()) };
  const fsMesh = new THREE.Mesh(quad, mFinal); fsMesh.frustumCulled = false; fsScene.add(fsMesh);
  let rtMain, rtA, rtB, rtC, rtD;
  const mkRT = (w, h, depth, type) => new THREE.WebGLRenderTarget(Math.max(2, w | 0), Math.max(2, h | 0), { type, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: depth, stencilBuffer: false });
  let rtType = isGL2 ? THREE.HalfFloatType : THREE.UnsignedByteType;
  if (isGL2) {   // certains appareils refusent le rendu en demi-flottants : on vérifie et on se rabat sur 8 bits
    const t = mkRT(4, 4, false, THREE.HalfFloatType); renderer.setRenderTarget(t);
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) rtType = THREE.UnsignedByteType;
    renderer.setRenderTarget(null); t.dispose();
  }
  R.hdr = rtType === THREE.HalfFloatType;
  R.resize = (cssW, cssH, dpr) => {
    R.dpr = dpr; R.w = Math.max(2, Math.round(cssW * dpr)); R.h = Math.max(2, Math.round(cssH * dpr)); R.cssW = cssW; R.cssH = cssH;
    renderer.setPixelRatio(1); renderer.setSize(R.w, R.h, false);
    camera.aspect = R.w / R.h; camera.updateProjectionMatrix();
    for (const t of [rtMain, rtA, rtB, rtC, rtD]) if (t) t.dispose();
    rtMain = mkRT(R.w, R.h, true, rtType); rtA = mkRT(R.w / 4, R.h / 4, false, rtType); rtB = mkRT(R.w / 4, R.h / 4, false, rtType); rtC = mkRT(R.w / 12, R.h / 12, false, rtType); rtD = mkRT(R.w / 12, R.h / 12, false, rtType);
    R.pxPerUnit = (R.h / 2) / Math.tan(FOV * DEG / 2);                         // px (appareil) par unité de rendu à profondeur 1
    R.viewUnits = CAM_D * Math.tan(FOV * DEG / 2) * Math.min(1, camera.aspect);   // unités de rendu correspondant au rayon du champ
    R.halfMin = Math.min(R.w, R.h) / 2;
  };
  const pass = (mat, target) => { fsMesh.material = mat; renderer.setRenderTarget(target); renderer.render(fsScene, fsCam); };

  /* ---- mise à jour d'une image ---- */
  const v3 = new THREE.Vector3(), camPos = new THREE.Vector3(), qF = new THREE.Quaternion(), qI = new THREE.Quaternion(), mB = new THREE.Matrix4();
  const place = (obj, o, unit, F) => { obj.position.set((o[0] - F.tg[0]) * F.s, (o[1] - F.tg[1]) * F.s, (o[2] - F.tg[2]) * F.s); obj.scale.setScalar(unit * F.s); };
  const ZERO = [0, 0, 0];
  R.project = (m, F, out) => {                                               // position (m, repère du Soleil) -> pixels CSS
    v3.set((m[0] - F.tg[0]) * F.s, (m[1] - F.tg[1]) * F.s, (m[2] - F.tg[2]) * F.s);
    const dx = v3.x - camPos.x, dy = v3.y - camPos.y, dz = v3.z - camPos.z;
    v3.applyMatrix4(camera.matrixWorldInverse); const zc = -v3.z; if (zc <= 0.05) return null;
    v3.applyMatrix4(camera.projectionMatrix);
    out[0] = (v3.x * 0.5 + 0.5) * R.cssW; out[1] = (0.5 - v3.y * 0.5) * R.cssH; out[2] = Math.sqrt(dx * dx + dy * dy + dz * dz); return out;
  };
  R.maxPointRadius = Math.min(maxPoint, 512) / 2;

  R.update = (F) => {
    const lr = F.logR, dpr = R.dpr, px = R.pxPerUnit, minPx = 0.95 * dpr, maxPx = R.maxPointRadius;
    // caméra : le plan de référence glisse de l'écliptique (petites échelles) au plan galactique (grandes échelles)
    qF.copy(qI).slerp(qFrameGal, F.frameMix);
    camPos.set(Math.cos(F.el) * Math.cos(F.az), Math.cos(F.el) * Math.sin(F.az), Math.sin(F.el)).applyQuaternion(qF).multiplyScalar(CAM_D);
    camera.position.copy(camPos); camera.up.set(0, 0, 1).applyQuaternion(qF); camera.lookAt(0, 0, 0); camera.updateMatrixWorld(true);
    const rMpc = F.R * F.aFac / (MPC * F.cos.a), gc = F.gcRel;

    // --- cosmos (comobile : tout est multiplié par le facteur d'échelle a(t)) ---
    const unitC = MPC * F.cos.a, horizon = F.cos.chiPH === null ? 1e9 : F.cos.chiPH;
    const sim = !!(F.opts.simWeb && web), oWeb = fadeIn(lr, 22.85, 23.5);
    if (web) { web.visible = far.visible = sim && oWeb > 0.003;
      if (web.visible) { place(web, gc, unitC, F); webU.uD.value = F.Dn; webU.uPx.value = px; webU.uOpacity.value = oWeb; webU.uCR.value = 0.6 * rMpc; webU.uHorizon.value = horizon; webU.uAge.value = F.age; webU.uMinPx.value = minPx * 1.25; webU.uMaxPx.value = Math.min(maxPx, 40 * dpr);
        place(far, gc, unitC, F); farU.uPx.value = px; farU.uOpacity.value = oWeb * 0.9; farU.uCR.value = 0.6 * rMpc; farU.uHorizon.value = horizon; farU.uAge.value = F.age; farU.uMinPx.value = minPx; } }
    surv.visible = !sim && oWeb > 0.003;
    if (surv.visible) { place(surv, gc, unitC, F); survU.uPx.value = px; survU.uOpacity.value = 0.36 * oWeb; survU.uMinPx.value = minPx; survU.uCR.value = 0.55 * rMpc; survU.uHorizon.value = horizon; survU.uAge.value = F.age; }
    { const k2 = clamp(Math.pow(350 / Math.max(rMpc, 1), 1.6), 0.03, 1); R.keep2 = k2; let extra = 0; for (const T of R.tiles) if (T.kind === 'gal') extra += T.draw * k2;      // galaxies en flux : de plus en plus nombreuses à mesure qu'on zoome
      if (surv.visible && extra > 0) survU.uOpacity.value *= Math.pow(svN / (svN + extra), 0.55);
      for (const T of R.tiles) if (T.kind === 'gal') { T.obj.visible = surv.visible && T.draw > 0; if (!T.obj.visible) continue; place(T.obj, gc, unitC, F); const u = T.u; u.uPx.value = survU.uPx.value; u.uOpacity.value = survU.uOpacity.value; u.uMinPx.value = survU.uMinPx.value; u.uCR.value = survU.uCR.value; u.uHorizon.value = survU.uHorizon.value; u.uAge.value = survU.uAge.value; u.uKeep.value = k2 * (Q.keep || 1); T.g.setDrawRange(0, T.draw); flushTile(T); } }
    const oNear = sim ? 0 : fadeIn(lr, 22.3, 22.9) * fadeOut(lr, 24.7, 25.3) * smoothstep(0.3, 1.2, F.age);
    near.visible = oNear > 0.003;
    if (near.visible) { place(near, gc, unitC, F); nearU.uPx.value = px; nearU.uOpacity.value = oNear; nearU.uMinPx.value = minPx * 1.35; nearU.uMaxPx.value = maxPx; nearU.uFloor.value = 0.55; nearU.uBigPx.value = Math.min(maxPx, 0.1 * R.halfMin); nearU.uStarCap.value = 2.4 * dpr; }
    const oLm = fadeIn(lr, 22.6, 23.2) * fadeOut(lr, LOG.MPC + 2.9, LOG.MPC + 3.5) * smoothstep(0.3, 1.2, F.age);
    landmarks.visible = sim && oLm > 0.003;
    if (landmarks.visible) { place(landmarks, gc, unitC, F); lmU.uPx.value = px; lmU.uOpacity.value = oLm * 0.9; lmU.uMinPx.value = minPx * 1.7; lmU.uMaxPx.value = maxPx; lmU.uFloor.value = 0.5; lmU.uBigPx.value = Math.min(maxPx, 0.1 * R.halfMin); lmU.uStarCap.value = 2.4 * dpr; }
    const horizonPhys = horizon * unitC;
    const oCmb = F.cos.chiPH === null ? 0 : fadeIn(lr, LOG.MPC + 3.1, LOG.MPC + 3.75) * fadeOut(horizonPhys / (F.R * F.aFac), 2.2, 5);
    cmb.visible = oCmb > 0.003;
    if (cmb.visible) { place(cmb, gc, horizonPhys, F); cmbU.uOpacity.value = oCmb; }
    const ring = (m, radM, op, widthPx) => {
      const rr = radM * F.s; m.visible = op > 0.003 && rr < CAM_D * 0.97 && rr > 1e-4;
      if (!m.visible) return; place(m, gc, 1, F); m.scale.setScalar(1); const u = m.userData.u;
      const sil = rr / Math.sqrt(1 - (rr / CAM_D) * (rr / CAM_D)); u.uRad.value = sil; u.uOpacity.value = op; u.uWidth.value = widthPx * dpr / Math.max(sil * px / CAM_D, 1);
    };
    const oHz = F.opts.horizons ? fadeIn(lr, LOG.MPC + 2.9, LOG.MPC + 3.5) : 0;
    ring(rings.hubble, F.cos.rHubble * MPC, isFinite(F.cos.rHubble) ? oHz * 0.75 : 0, 1.1);
    ring(rings.event, F.cos.chiEH === null ? 0 : F.cos.chiEH * unitC, F.cos.chiEH === null ? 0 : oHz * 0.85, 1.1);
    ring(rings.particle, horizonPhys, F.cos.chiPH === null ? 0 : fadeIn(lr, LOG.MPC + 3.1, LOG.MPC + 3.75) * 0.6, 1.0);
    // repère « vous êtes ici » : un anneau de taille fixe à l'écran dès que le Soleil n'est plus qu'un point
    { const oH = fadeIn(lr, 19.6, 20.2); const m = rings.here; m.visible = oH > 0.003;
      if (m.visible) { place(m, lr > 22.0 ? gc : ZERO, 1, F); m.scale.setScalar(1); const u = m.userData.u; const rr = 9 * dpr * CAM_D / px; u.uRad.value = rr; u.uOpacity.value = oH * 0.9; u.uWidth.value = 1.2 / 9; } }

    // --- Voie lactée, halo, Groupe local (liés par la gravité : ne suivent pas l'expansion) ---
    const born = smoothstep(0.5, 1.6, F.age), bigRel = Math.min(maxPx, 0.1 * R.halfMin), small = lerp(1, 0.5, smoothstep(21.5, 22.5, lr));
    const setGal = (obj, u, origin, unit, op, floor, minMul, bigPx) => { obj.visible = op > 0.003; if (!obj.visible) return; place(obj, origin, unit, F); u.uT1.value = F.T1; u.uT2.value = F.T2; u.uPx.value = px; u.uOpacity.value = op; u.uMinPx.value = minPx * (minMul || 1); u.uMaxPx.value = maxPx; u.uFloor.value = floor; u.uBigPx.value = bigPx || bigRel; u.uStarCap.value = 2.4 * dpr; };
    const galPx = 15 * KPC * F.s * px / CAM_D / dpr, exag = F.opts.realSize ? 1 : clamp(13 / Math.max(galPx, 1e-9), 1, 3.2);
    mwU.uExag.value = lgU.uExag.value = exag; R.galExag = exag;
    const inside = lerp(0.2, 1, smoothstep(18.2, 20.3, lr));
    const mgK = F.mergeK || 0;
    setGal(galaxy, mwU, gc, KPC, born * inside * small * (1 - mgK) * fadeOut(lr, 23.0, 23.7), lerp(lerp(0.38, 0.02, smoothstep(18.4, 21, lr)), 0.0012, smoothstep(21.6, 22.6, lr)), lerp(2.3, 1, smoothstep(18.2, 20.3, lr)));
    mwU.uInside.value = 1 - smoothstep(18.2, 20.3, lr);
    { const c = G.lg.m31.c, o = [gc[0] + c[0] * KPC, gc[1] + c[1] * KPC, gc[2] + c[2] * KPC], fl = lerp(0.25, 0.012, smoothstep(20.5, 22.3, lr));
      setGal(m31, m31U, o, KPC, born * lerp(0.4, 1, smoothstep(19.5, 21.3, lr)) * small * (1 - mgK) * fadeOut(lr, 23.5, 24.2), fl, 1.1); m31U.uExag.value = exag;
      if (!F.dyn) for (const h of cores) h[0].visible = false;
      if (dyn) { const on = F.dyn ? 1 : 0, flo = lerp(lerp(0.38, 0.02, smoothstep(18.4, 21, lr)), 0.0012, smoothstep(21.6, 22.6, lr));
        const dim = lerp(1, 0.55, smoothstep(21.2, 22.0, lr)), oD = on * born * inside * small * dim * fadeOut(lr, 23.0, 23.7);
        setGal(dyn, dynU, gc, KPC, oD * (F.dyn ? F.dyn.boost : 1), flo * 0.5, lerp(1.25, 1, smoothstep(18.2, 20.3, lr)));
        for (const h of cores) { const m = h[0], c = h[1]; m.visible = oD > 0.004; if (!m.visible) continue; place(m, c ? [gc[0] + c[0] * KPC, gc[1] + c[1] * KPC, gc[2] + c[2] * KPC] : gc, 1, F); m.scale.setScalar(1); m.userData.u.uRad.value = Math.min(26 * KPC * F.s, 300); m.userData.u.uOpacity.value = oD * 0.22; }
        if (dyn.visible) { dynU.uExag.value = 1; dynU.uInside.value = mwU.uInside.value; dyn.geometry.attributes.position.needsUpdate = true; } }
      if (F.lgSh) { const a = lgU.uSh.value, q = F.lgSh; for (let i = 0; i < a.length; i++) a[i].set(q[i * 3], q[i * 3 + 1], q[i * 3 + 2]); }
      lgU.uShift.value.set(F.lgShift[0], F.lgShift[1], F.lgShift[2]); lgU.uShift2.value.set(F.lgShift2[0], F.lgShift2[1], F.lgShift2[2]); lgU.uG2.value = 1 - F.lmcGone; }
    setGal(localGroup, lgU, gc, KPC, born * lerp(0.4, 1, smoothstep(19.5, 21.3, lr)) * small * fadeOut(lr, 23.5, 24.2), lerp(0.25, 0.012, smoothstep(20.5, 22.3, lr)), 1.1);
    { const oH = born * fadeIn(lr, 20.1, 20.7) * fadeOut(lr, 23.0, 23.7) * F.dmMix;
      for (const h of halos) { const m = h[0], c = h[1]; m.visible = oH > 0.004; if (!m.visible) continue; place(m, c ? [gc[0] + c[0] * KPC, gc[1] + c[1] * KPC, gc[2] + c[2] * KPC] : gc, 1, F); m.scale.setScalar(1); m.userData.u.uRad.value = Math.min(260 * KPC * F.s, 300); m.userData.u.uOpacity.value = oH * 0.05; } }

    // --- étoiles ---
    const unitToPc = 1 / (F.s * PC), expo = Math.min(5 * Math.log10(Math.max(F.R, 2.5 * PC) / (2.5 * PC)) * 0.93, 1.9);
    const setStar = (obj, u, op) => { obj.visible = op > 0.003; if (!obj.visible) return; place(obj, ZERO, LY, F); u.uUnitToPc.value = unitToPc; u.uExpo.value = expo; u.uOpacity.value = op; u.uDpr.value = dpr; };
    setStar(stars, starsU, born * fadeOut(lr, 19.5, 20.3)); starsU.uT.value = F.tMyr; starsU.uFlash.value = F.flash;
    setStar(stars2, stars2U, born * fadeOut(lr, 19.5, 20.3)); stars2U.uT.value = F.tMyr; stars2U.uFlash.value = F.flash;
    if (stars2.visible) { if (Math.abs(F.ty - star2PassT) > 25) { star2PassT = F.ty; star2Done = 0; }        // inutile de recalculer pour quelques années d'écart
      if (star2Done < gN) { const n = Math.ceil(gN / ((Q.starChunks || 8) * 3)), i1 = Math.min(gN, star2Cursor + n); starPositions(K2, F.ty, F.tEff, gPos, star2Cursor, i1); star2Done += i1 - star2Cursor; star2Cursor = i1 >= gN ? 0 : i1; stars2.geometry.attributes.position.needsUpdate = true; } }
    { const nearT = fadeOut(Math.abs(F.ty), 3e6, 1.5e7); let fr = false;
      for (const T of R.tiles) if (T.kind === 'star') { const root = T.grp || T.obj; setStar(root, T.u, T.n > 0 ? 0.6 * born * nearT * fadeOut(lr, 19.5, 20.3) : 0); if (!root.visible) { T.drawn = 0; continue; }
        T.u.uVt.value = F.ty * 2 * KMS_LY_YR; T.u.uMcut.value = R.mcut; flushTile(T);
        if (!T.grp) { T.g.setDrawRange(0, T.draw); T.drawn = T.draw; }
        else { if (!fr) { fr = true; camera.matrixWorldInverse.copy(camera.matrixWorld).invert(); PMX.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse); FRU.setFromProjectionMatrix(PMX); } cellPass(T, F, unitToPc, expo); } } }
    { const tx = F.tg[0] / LY, ty = F.tg[1] / LY, tz = F.tg[2] / LY, rr = F.nearR || 0; for (const u of [starsU, stars2U]) { u.uTgt.value.set(tx, ty, tz); u.uTgtR.value = rr; } for (const T of R.tiles) if (T.kind === 'star') { T.u.uTgt.value.set(tx, ty, tz); T.u.uTgtR.value = rr; }
      const L = F.nearStars || [], pxu = R.viewUnits / (0.5 * Math.min(R.cssW || 800, R.cssH || 600));
      for (let k = 0; k < nearPool.length; k++) { const m = nearPool[k][0], u = nearPool[k][1], p = L[k]; m.visible = !!p && F.nearK > 0.01; if (!m.visible) continue; place(m, p.pos, 1, F); m.scale.setScalar(1);
        const rs = p.radM * F.s, half = Math.max(rs * 2.4, 26 * pxu); u.uRad.value = half; u.uDisc.value = clamp(rs / half, 0.003, 0.6); u.uColor.value.setRGB(p.col[0], p.col[1], p.col[2]); u.uOpacity.value = F.nearK; } }
    {      // positions des étoiles : recalculées par tranches, pour étaler le coût (même couche masquée : étiquettes et clics en dépendent)
      if (F.ty !== starPassT) { starPassT = F.ty; starDone = 0; if (R.keyStars) for (const i of R.keyStars) starPositions(K, F.ty, F.tEff, sPos, i, i + 1); }      // étoiles nommées ou sélectionnées : toujours à jour
      if (starDone < sN) { const n = Math.ceil(sN / (Q.starChunks || 8)), i1 = Math.min(sN, starCursor + n); starPositions(K, F.ty, F.tEff, sPos, starCursor, i1); starDone += i1 - starCursor; starCursor = i1 >= sN ? 0 : i1; stars.geometry.attributes.position.needsUpdate = true; } }
    const still = fadeOut(Math.abs(F.ty), 3e6, 1.5e7);
    setStar(clusters, clusU, born * still * fadeIn(lr, 16.6, 17.4) * fadeOut(lr, 21.2, 21.8)); clusU.uExpo.value = Math.min(expo, 1.1) + 2.87 * Math.log10(Math.max(F.R, 300 * PC) / (300 * PC));
    const solarAlive = F.sunAlive, sysK = F.sysK === undefined ? 1 : F.sysK;      // sysK : petits corps et nuage d'Oort, dispersés avec les planètes
    setStar(sunStar, sunStarU, solarAlive * fadeIn(lr, 13.6, 14.6) * fadeOut(lr, 19.6, 20.3));
    sunStarU.uExpo.value = expo + 0.6;
    { const a = sunStar.geometry.attributes, m = 4.83 - 2.5 * Math.log10(Math.max(F.sun.L, 1e-7)); if (Math.abs(a.aMag.array[0] - m) > 0.01) { a.aMag.array[0] = m; a.aMag.needsUpdate = true; const c = F.sunCol; a.aCol.array.set([0.3 + 0.7 * c[0], 0.3 + 0.7 * c[1], 0.3 + 0.7 * c[2]]); a.aCol.needsUpdate = true; } }
    { const m = rings.sel; m.visible = !!F.selPos; if (m.visible) { place(m, F.selPos, 1, F); m.scale.setScalar(1); const u = m.userData.u, depth = m.position.distanceTo(camPos); u.uRad.value = 11 * dpr * depth / px; u.uOpacity.value = 0.95; u.uWidth.value = 1.3 / 11; } }
    R.vis = { stars: stars.visible ? starsU.uOpacity.value : 0, clusters: clusters.visible ? clusU.uOpacity.value : 0, near: oNear, surv: surv.visible ? oWeb : 0, lg: localGroup.visible ? lgU.uOpacity.value : 0 };
    R.expo = expo; R.expoC = clusU.uExpo.value; R.unitToPc = unitToPc; R.survCR = 0.55 * rMpc; R.unitC = unitC;

    // --- système solaire ---
    const oSol = solarAlive * fadeOut(lr, 14.0, 14.9);
    const oOort = solarAlive * sysK * fadeIn(lr, 13.7, 14.7) * fadeOut(lr, 16.45, 17.0); oort.visible = oOort > 0.003;
    if (oort.visible) { place(oort, ZERO, AU, F); oortU.uOpacity.value = oOort * 0.5; oortU.uDpr.value = dpr; }
    const oBelt = solarAlive * sysK * fadeIn(lr, 10.2, 11.0) * fadeOut(lr, 13.2, 13.9) * fadeOut(F.stepYears, 0.25, 0.9) * lerp(1, 0.3, smoothstep(11.8, 12.8, lr)), oKu = solarAlive * sysK * fadeIn(lr, 11.3, 12.2) * fadeOut(lr, 13.9, 14.7) * fadeOut(F.stepYears, 12, 45);
    belt.visible = oBelt > 0.003; kuiper.visible = oKu > 0.003; R.beltVis = oBelt; R.kuiperVis = oKu; R.tick = (R.tick || 0) + 1;
    if (belt.visible && (!kuiper.visible || R.tick % 2 === 0 || !AST.done)) { updateBodies(AST, F.jd); AST.done = true; belt.geometry.attributes.position.needsUpdate = true; }
    if (kuiper.visible && (!belt.visible || R.tick % 2 === 1 || !TNO.done)) { updateBodies(TNO, F.jd); TNO.done = true; kuiper.geometry.attributes.position.needsUpdate = true; }
    if (belt.visible) { place(belt, ZERO, AU * F.orb, F); beltU.uOpacity.value = oBelt; beltU.uDpr.value = dpr; }
    if (kuiper.visible) { place(kuiper, ZERO, AU * F.orb, F); kuiperU.uOpacity.value = oKu * 0.85; kuiperU.uDpr.value = dpr; }
    for (const T of R.tiles) if (T.kind === 'ast') { T.obj.visible = oBelt > 0.003 && T.n > 0; if (!T.obj.visible) continue; place(T.obj, ZERO, AU * F.orb, F);      // vus de loin, les points se superposent : on baisse leur éclat pour ne pas saturer
      T.u.uOpacity.value = oBelt * 0.5 * clamp(Math.pow(4 * AU / Math.pow(10, lr), 2), 0.015, 1); T.u.uDpr.value = dpr; T.u.uT.value = F.jd - T.epoch; T.g.setDrawRange(0, T.n); flushTile(T); } R.astVis = oBelt;
    { const oCom = Math.max(oBelt, oKu); comets.visible = oCom > 0.003; R.comVis = comets.visible ? oCom : 0;
      if (comets.visible) { place(comets, ZERO, AU * F.orb, F); cometU.uOpacity.value = oCom; cometU.uDpr.value = dpr; if (R.tick % 2 === 0 || !COM.done) { updateComets(COM, F.days); COM.done = true; comets.geometry.attributes.position.needsUpdate = true; } } }
    { const oE = born * still * fadeIn(lr, 16.2, 16.9) * fadeOut(lr, 19.7, 20.4) * 0.9, oP = born * still * fadeIn(lr, 18.7, 19.4) * fadeOut(lr, 21.3, 21.9) * 0.9;
      exo.visible = oE > 0.003; if (exo.visible) { place(exo, ZERO, LY, F); exoU.uOpacity.value = oE; exoU.uDpr.value = dpr; }
      psr.visible = oP > 0.003; if (psr.visible) { place(psr, ZERO, LY, F); psrU.uOpacity.value = oP; psrU.uDpr.value = dpr; } R.exoVis = oE; R.psrVis = oP; }
    { const oB = born * still * fadeIn(lr, 17.4, 18.1) * fadeOut(lr, 21.4, 22.0), oM = born * fadeIn(lr, 22.2, 22.9) * fadeOut(lr, 25.2, 25.8);
      bhs.visible = oB > 0.003; if (bhs.visible) { place(bhs, ZERO, LY, F); bhsU.uOpacity.value = oB; bhsU.uDpr.value = dpr; }
      bhm.visible = oM > 0.003; if (bhm.visible) { place(bhm, gc, unitC, F); bhmU.uOpacity.value = oM; bhmU.uDpr.value = dpr; } R.bhsVis = oB; R.bhmVis = oM;
      selLine.visible = !!selOrb && lr < 16.2 && lr > (selOrb.c ? 6.2 : 9.5);
      if (selLine.visible) { place(selLine, selOrb.c ? selOrb.c() : ZERO, selOrb.c ? AU : AU * F.orb, F); const w = renderer.domElement.width, h = renderer.domElement.height; for (const [u, d] of selOff) u.uOff.value.set(d[0] * 1.5 / w, d[1] * 1.5 / h); }
      R.constVis = F.constOn ? born * fadeIn(lr, 10.8, 11.6) * fadeOut(lr, 17.3, 18.2) * fadeOut(Math.abs(F.ty), 3e4, 1.2e5) * fadeOut(Math.hypot(F.tg[0], F.tg[1], F.tg[2]) / LY, 0.4, 1.5) : 0; if (cons) { cons.visible = R.constVis > 0.003; if (cons.visible) { place(cons, ZERO, LY, F); consU.uOpacity.value = 0.4 * R.constVis; cons.geometry.attributes.position.needsUpdate = true; } }
      let mv = 0;      // objets suivis sur leur orbite : chaque groupe a sa plage d'échelles ; certains ne s'affichent que si la vue est centrée près d'eux
      for (const k in moonSets) { const m = moonSets[k], t = m.s, c = F.moonC && F.moonC[k]; let op = c ? born * fadeIn(lr, t.lr[0], t.lr[1]) * fadeOut(lr, t.lr[2], t.lr[3]) : 0;
        if (op > 0 && t.near) op *= fadeOut(Math.log10(Math.max(Math.hypot(c[0] - F.tg[0], c[1] - F.tg[1], c[2] - F.tg[2]), 1)) - lr, 1.2, 1.7);
        t.vis = op; m.o.visible = op > 0.003; if (t.kind === 'moon') mv = Math.max(mv, op); if (!m.o.visible) continue; place(m.o, c, AU, F); m.u.uOpacity.value = op; m.u.uDpr.value = dpr; m.o.geometry.attributes.position.needsUpdate = true; }
      { const t = moonSets['exo:exo'], c = F.moonC && F.moonC['exo:exo'], op = t && c ? t.s.vis : 0; sysLines.visible = sysOn && op > 0.003; if (sysLines.visible) { place(sysLines, c, AU, F); sysU.uOpacity.value = 0.85 * op; }
        sysStar.visible = !!c && op > 0.003; if (sysStar.visible) { place(sysStar, c, 1, F); sysStar.scale.setScalar(1); const u = sysStar.userData.u; u.uRad.value = 18 * dpr * CAM_D / px; u.uOpacity.value = op; } }
      { const hd = F.photoHide; if (hd) { lgU.uHide.value.set(hd.c[0], hd.c[1], hd.c[2]); lgU.uHideK.value = hd.k; } else lgU.uHideK.value = 0;
        if (F.m31Hide > 0) { const k = 1 - 0.94 * F.m31Hide; m31U.uOpacity.value *= k; for (const h of [cores[1], halos[1]]) if (h[0].visible) h[0].userData.u.uOpacity.value *= k; } }
      { const L = F.photos || []; gvBusy = 0; gvCache.forEach(M => { if (M) M.pts.visible = false; }); for (let k = 0; k < phPool.length; k++) { const m = phPool[k][0], u = phPool[k][1], p = L[k]; m.visible = !!p && !!phTex[p.atlas] && p.op > 0.01; if (!m.visible) continue; const M = gvGet(p); if (M) gvDraw(M, p, F, dpr); const s = F.s, hs = p.half * s;
          u.uC.value.set((p.c[0] - F.tg[0]) * s, (p.c[1] - F.tg[1]) * s, (p.c[2] - F.tg[2]) * s); u.uE.value.set(p.e[0] * hs, p.e[1] * hs, p.e[2] * hs); u.uN.value.set(p.n[0] * hs, p.n[1] * hs, p.n[2] * hs); u.uTex.value = phTex[p.atlas]; u.uCell.value.set(p.uv[0], p.uv[1], p.uv[2], p.uv[2]); u.uOpacity.value = p.op; u.uFloor.value = p.floor;
          if (M) { if (M.ty === 'D') { if (M.edgeW > 0.97) m.visible = false; u.uE.value.set(M.A[0] * hs, M.A[1] * hs, M.A[2] * hs); u.uN.value.set(M.B[0] * hs, M.B[1] * hs, M.B[2] * hs); u.uOpacity.value = p.op * (1 - M.edgeW) * 0.9; } else { const dx = u.uC.value.x - camPos.x, dy = u.uC.value.y - camPos.y, dz = u.uC.value.z - camPos.z, ca = Math.abs(dx * M.L[0] + dy * M.L[1] + dz * M.L[2]) / (Math.hypot(dx, dy, dz) || 1); u.uOpacity.value = p.op * 0.6 * Math.pow(ca, 6); } } } }
      { egQ.visible = !!F.glow; if (F.glow) egU.uColor.value.setRGB(F.glow[0], F.glow[1], F.glow[2]);
        const sh = F.shadow, so = sh ? fadeIn(lr, 7.4, 8.0) * fadeOut(lr, 9.9, 10.5) : 0; sxL.visible = so > 0.01;
        if (sxL.visible) { const s = F.s, L = 6e8, P = [sh[0], [sh[0][0] + sh[1][0] * L, sh[0][1] + sh[1][1] * L, sh[0][2] + sh[1][2] * L], sh[2], [sh[2][0] + sh[3][0] * L * 1.6, sh[2][1] + sh[3][1] * L * 1.6, sh[2][2] + sh[3][2] * L * 1.6]];
          for (let k = 0; k < 4; k++) for (let j = 0; j < 3; j++) sxP[k * 3 + j] = (P[k][j] - F.tg[j]) * s; sxG.attributes.position.needsUpdate = true; sxU.uOpacity.value = 0.6 * so; } }
      { const k = F.skyOn && skyReady ? fadeIn(lr, 6.6, 7.2) * fadeOut(lr, 18.0, 19.0) * fadeOut(Math.hypot(F.tg[0], F.tg[1], F.tg[2]) / LY, 400, 2500) * fadeOut(Math.abs(F.ty), 3e5, 2e6) : 0; skyMesh.visible = k > 0.003; skyU.uGain.value = 1.25 * k; }
      R.moonVis = mv; }

    const sol = F.sol, d = F.days;
    const orb = F.orb, mg = sol.moonGeo, sc3 = (p, k) => [p[0] * k, p[1] * k, p[2] * k];
    const oP = k => (F.orbP && F.orbP[k]) || orb;      /* R5 : Mercure et Vénus ont leur propre facteur d'orbite (spirale calculée) */
    const posOf = k => k === 'sun' ? ZERO : k === 'earth' ? sc3(sol.earth, oP('earth')) : k === 'moon' ? [sol.earth[0] * oP('earth') + mg[0], sol.earth[1] * oP('earth') + mg[1], sol.earth[2] * oP('earth') + mg[2]] : sc3(sol.planets[k].pos, oP(k));
    for (const b of BODIES) {
      const o = bodies[b.key], pa = posOf(b.key);
      o.pos[0] = pa[0] * AU; o.pos[1] = pa[1] * AU; o.pos[2] = pa[2] * AU;
      const g = o.grp; g.position.set((o.pos[0] - F.tg[0]) * F.s, (o.pos[1] - F.tg[1]) * F.s, (o.pos[2] - F.tg[2]) * F.s);
      const depth = g.position.distanceTo(camPos), pxWorld = depth / px;
      const real = b.r * 1e3 * (b.key === 'sun' ? F.sun.R : 1) * F.s, mini = (F.opts.realSize ? Math.min(b.minPx, 1.1) : b.minPx) * dpr * pxWorld * (b.key === 'sun' && F.sun.R < 0.05 ? 0.35 : 1);
      let vis = F.eng[b.key === 'moon' ? 'earth' : b.key] ? 0 : oSol;
      if (b.key !== 'sun') { const per = b.key === 'moon' ? 0.0748 : b.key === 'earth' ? 1 : sol.planets[b.key].period; vis *= fadeOut(F.stepYears / per, 0.06, 0.2); }
      if (b.key === 'moon') { const sep = Math.hypot(o.pos[0] - bodies.earth.pos[0], o.pos[1] - bodies.earth.pos[1], o.pos[2] - bodies.earth.pos[2]) * F.s / pxWorld / dpr; vis *= smoothstep(7, 14, sep); }
      o.vis = vis; o.rRender = Math.max(real, mini); o.px = o.rRender / pxWorld / dpr; o.exag = o.rRender / Math.max(real, 1e-30);
      g.visible = vis > 0.01 && o.rRender > 0; if (!g.visible) continue;
      g.scale.setScalar(o.rRender);
      if (b.key === 'moon') {                                            // rotation synchrone : la même face vers la Terre
        const e = bodies.earth.pos, x = vnorm([e[0] - o.pos[0], e[1] - o.pos[1], e[2] - o.pos[2]]), z0 = vcross(x, [0, 0, 1]), y = vnorm(vcross(vnorm(z0), x));
        const z = vcross(x, y); mB.set(x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, 0, 0, 0, 1); o.spin.quaternion.setFromRotationMatrix(mB);
      } else {
        const W = ((b.w0 + ((b.w1 * d) % 360)) % 360) * DEG, cw = Math.cos(W), sw = Math.sin(W), n = o.node, m = o.merid, y = o.pole;
        const x = [n[0] * cw + m[0] * sw, n[1] * cw + m[1] * sw, n[2] * cw + m[2] * sw], z = vcross(x, y);
        mB.set(x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, 0, 0, 0, 1); o.spin.quaternion.setFromRotationMatrix(mB);
      }
      if (b.key === 'sun') { o.u.uTime.value = F.wall; const sk = smoothstep(0.03, 0.3, b.r * 1e3 * F.sun.R * F.s / R.viewUnits); o.u.uGain.value = 7 * clamp(Math.pow(F.sun.T / 5774, 1.5), 0.35, 2.5) * lerp(1, 0.33, sk) * (F.sun.R < 0.05 ? clamp((F.sun.T - 1500) / 9000, 0.1, 1) : 1); o.u.uDet.value = 1 + 2.2 * sk; const c = F.sunCol; o.u.uColor.value.set(lerp(1, c[0], 0.8), lerp(1, c[1], 0.8) * 0.93, lerp(1, c[2], 0.8) * 0.82).lerp(sunWarm, 0.85 * sk); }
      else {
        const sd = vnorm([-o.pos[0], -o.pos[1], -o.pos[2]]); o.u.uSun.value.set(sd[0], sd[1], sd[2]);
        o.u.uSpin.value = b.w1 ? smoothstep(0.5, 1.6, Math.abs(b.w1) * DEG * F.stepYears * 365.25) : 0;
        if (o.ringU) { for (const c of o.spin.children) if (c !== o.mesh) c.visible = !F.ringsGone; o.ringU.uSun.value.set(sd[0], sd[1], sd[2]); o.ringU.uCenter.value.copy(g.position); o.ringU.uPlanetR.value = o.rRender; o.ringU.uNormal.value.set(o.pole[0], o.pole[1], o.pole[2]); }
      }
    }
    { const s = bodies.sun, g = s.grp; glow.visible = oSol > 0.01; if (glow.visible) { glow.position.copy(g.position); const depth = g.position.distanceTo(camPos); glowU.uRad.value = Math.max(s.rRender * 9, 24 * dpr * depth / px); glowU.uOpacity.value = oSol * lerp(0.9, 0.35, smoothstep(40, 400, s.px)) * clamp(Math.pow(Math.max(F.sun.L, 1e-9), 0.3), 0.04, 1.4); glowU.uColor.value.setRGB(lerp(1, F.sunCol[0], 0.6), lerp(0.86, F.sunCol[1], 0.6), lerp(0.66, F.sunCol[2], 0.6)); glowU.uCore.value = 1 / Math.pow(Math.max(s.rRender * 1.05 / glowU.uRad.value, 0.02), 2); } }
    // orbites : rubans calculés dans le shader, ancrés exactement sur la planète
    const oOrb = F.opts.orbits ? solarAlive * fadeOut(lr, 13.5, 14.5) : 0;
    for (const k of ORBIT_KEYS) {
      const m = orbits[k], st = sol.planets[k], u = m.userData.u, body = k === 'emb' ? bodies.earth : bodies[k];
      const close = fadeIn(lr, Math.log10(st.a * AU) - 2.6, Math.log10(st.a * AU) - 1.7);
      m.visible = oOrb * close > 0.004 && !F.eng[k === 'emb' ? 'earth' : k]; if (!m.visible) continue;
      const ok = oP(k === 'emb' ? 'earth' : k); place(m, [st.pos[0] * AU * ok, st.pos[1] * AU * ok, st.pos[2] * AU * ok], AU * ok, F);
      const b = st.a * Math.sqrt(1 - st.e * st.e); u.uP.value.set(st.P[0] * st.a, st.P[1] * st.a, st.P[2] * st.a); u.uQ.value.set(st.Q[0] * b, st.Q[1] * b, st.Q[2] * b);
      u.uE0.value = st.E; u.uWidth.value = 0.85 * dpr; u.uViewport.value.set(R.w, R.h); u.uOpacity.value = oOrb * close * lerp(0.5, 0.85, 1 - body.vis) * 0.62;
    }
    { const m = orbits.moon, u = m.userData.u, mg = sol.moonGeo, r = vlen(mg), close = fadeIn(lr, 7.0, 7.6) * fadeOut(lr, 10.1, 10.9);
      m.visible = oOrb * close > 0.004 && bodies.moon.vis > 0.02;
      if (m.visible) { const x = vnorm(mg), nrm = vnorm([Math.sin(5.145 * DEG) * Math.sin((125.04 - 0.0529538 * d) * DEG), -Math.sin(5.145 * DEG) * Math.cos((125.04 - 0.0529538 * d) * DEG), Math.cos(5.145 * DEG)]), y = vnorm(vcross(nrm, x));
        place(m, bodies.moon.pos, AU, F); u.uP.value.set(x[0] * r, x[1] * r, x[2] * r); u.uQ.value.set(y[0] * r, y[1] * r, y[2] * r); u.uE0.value = 0; u.uWidth.value = 0.8 * dpr; u.uViewport.value.set(R.w, R.h); u.uOpacity.value = oOrb * close * 0.45; } }
    R.bodies = bodies; R.camPos = camPos; micro.update(F);
  };

  const micro = initMicro(THREE, scene, camera, R, Q); R.micro = micro; R.scene = scene;
  R.projectLocal = (m, F, out) => {                                          // position (m, autour du point visé) -> pixels CSS, pour l'infiniment petit
    v3.set(m[0] * F.sT, m[1] * F.sT, m[2] * F.sT).applyMatrix4(camera.matrixWorldInverse); if (-v3.z <= 0.05) return null;
    v3.applyMatrix4(camera.projectionMatrix); out[0] = (v3.x * 0.5 + 0.5) * R.cssW; out[1] = (0.5 - v3.y * 0.5) * R.cssH; out[2] = 0; return out;
  };
  /* ---- S6 : lentille d'un trou noir (Sagittarius A*, M87*) quand la caméra en est à moins de LENS_RON fois GM/c² (au-delà, la déviation
     fait moins d'un pixel) ; vue tout autour (pour les sources hors de l'image) seulement sous LENS_RCUBE ---- */
  const LENS_RON = 1e7, LENS_RCUBE = 3000, lensCam = [0, 0, 0], lensDir = new THREE.Vector3(), lensM87 = DATA.BHM.names.indexOf('M87');
  let lensRT = null, lensCam3 = null, lensTex = null, lensR = 0, lensTick = 0;
  R.lens = { on: false, inside: false, name: null, r: 0, dirty: true, key: null, keyAt: 0 };
  function lensCandidates(F) {
    const out = [{ name: 'Sagittarius A*', pos: F.gcRel, M: Math.pow(10, DATA.SGRA_LOGM || 6.63) }], i = lensM87;
    if (i >= 0) { const k = MPC * F.cos.a, p = R.BHM.pos; out.push({ name: 'M87*', pos: [F.gcRel[0] + p[i * 3] * k, F.gcRel[1] + p[i * 3 + 1] * k, F.gcRel[2] + p[i * 3 + 2] * k], M: 6.5e9 }); }      /* M87* : masse de l'EHT 2019, comme sa fiche */
    return out;
  }
  R.lensUpdate = F => {
    const L = R.lens; L.on = L.inside = false; if (!F || !F.gcRel || !isGL2) return;
    for (let c = 0; c < 3; c++) lensCam[c] = F.tg[c] + camPos.getComponent(c) / F.s;
    let best = null; for (const b of lensCandidates(F)) { const r = Math.hypot(b.pos[0] - lensCam[0], b.pos[1] - lensCam[1], b.pos[2] - lensCam[2]) / (GM_C2_SUN * b.M); if (!best || r < best.r) best = Object.assign({ r }, b); }
    if (R.lensForceR) best.r = R.lensForceR;      /* crochet de test */
    if (!best || best.r > LENS_RON) return;
    L.on = true; L.name = best.name; L.r = best.r; L.inside = best.r < LENS_RMIN;
    if (L.inside) return;
    const cube = best.r < LENS_RCUBE, f = mFinal.uniforms;
    if (cube) { const now = performance.now(), key = [lensCam[0], lensCam[1], lensCam[2], F.ty, F.s], k0 = L.key, rm = best.r * GM_C2_SUN * best.M;
      const moved = !k0 || key[4] !== k0[4] || Math.hypot(key[0] - k0[0], key[1] - k0[1], key[2] - k0[2]) > 0.002 * rm, aged = k0 && key[3] !== k0[3] && now - L.keyAt > 500;      /* date qui défile : vue tout autour refaite deux fois par seconde au plus */
      if (moved || aged) { L.key = key; L.keyAt = now; L.dirty = true; } }
    if (!lensTex) { lensTex = new THREE.DataTexture(new Float32Array(512 * 4), 512, 1, THREE.RGBAFormat, THREE.FloatType); lensTex.minFilter = lensTex.magFilter = THREE.NearestFilter; }
    if (cube && !lensRT) { L.dirty = true; lensRT = new THREE.WebGLCubeRenderTarget(R.w > 1200 ? 256 : 128, { type: rtType, format: THREE.RGBAFormat, generateMipmaps: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter }); lensCam3 = new THREE.CubeCamera(0.01, 2e7, lensRT); }
    if (Math.abs(best.r / (lensR || 1) - 1) > 0.01) {      /* table refaite à 1 % de distance près (environ 4 ms) : ombre juste à 1 % près entre deux tables */ const T = lensLut(best.r, 512), d = lensTex.image.data; for (let i = 0; i < 512; i++) d[i * 4] = T.alpha[i]; lensTex.needsUpdate = true; lensR = best.r; f.uPsiC.value = T.psiC; f.uLl.value.set(T.l0, T.l1); }
    lensDir.set((best.pos[0] - F.tg[0]) * F.s - camPos.x, (best.pos[1] - F.tg[1]) * F.s - camPos.y, (best.pos[2] - F.tg[2]) * F.s - camPos.z).normalize().transformDirection(camera.matrixWorldInverse);
    const t = Math.tan(FOV * DEG / 2); f.uBH.value.copy(lensDir); f.uTanF.value.set(t * camera.aspect, t); f.uRot.value.setFromMatrix4(camera.matrixWorld); f.tLut.value = lensTex; f.uCubeOn.value = cube ? 1 : 0; if (cube) f.tCube.value = lensRT.texture;
  };
  R.render = (wall, exposure) => {
    const lc = R.lens.on && !R.lens.inside && mFinal.uniforms.uCubeOn.value > 0.5;
    if (lc && R.lens.dirty && (lensTick++ % 8 === 0)) { lensCam3.position.copy(camPos); lensCam3.update(renderer, scene); R.lens.dirty = false; }      /* vue tout autour (sources hors de l’image) : six rendus en plus, seulement quand elle a changé */
    mFinal.uniforms.uLens.value = !R.lens.on ? 0 : R.lens.inside ? 2 : 1;
    renderer.setRenderTarget(rtMain); renderer.clear(); renderer.render(scene, camera);
    if (R.bloom) {
      mBright.uniforms.tMap.value = rtMain.texture; mBright.uniforms.uTexel.value.set(1 / R.w, 1 / R.h); mBright.uniforms.uThresh.value = R.hdr ? 1.0 : 0.72; pass(mBright, rtA);
      mBlur.uniforms.tMap.value = rtA.texture; mBlur.uniforms.uDir.value.set(1 / rtA.width, 0); pass(mBlur, rtB);
      mBlur.uniforms.tMap.value = rtB.texture; mBlur.uniforms.uDir.value.set(0, 1 / rtA.height); pass(mBlur, rtA);
      mBlur.uniforms.tMap.value = rtA.texture; mBlur.uniforms.uDir.value.set(1 / rtC.width, 0); pass(mBlur, rtC);
      mBlur.uniforms.tMap.value = rtC.texture; mBlur.uniforms.uDir.value.set(0, 1 / rtC.height); pass(mBlur, rtD);
      mBlur.uniforms.tMap.value = rtD.texture; mBlur.uniforms.uDir.value.set(1.6 / rtC.width, 0); pass(mBlur, rtC);
      mBlur.uniforms.tMap.value = rtC.texture; mBlur.uniforms.uDir.value.set(0, 1.6 / rtC.height); pass(mBlur, rtD);
    }
    const f = mFinal.uniforms; f.tMap.value = rtMain.texture; f.tB1.value = rtA.texture; f.tB2.value = rtD.texture; f.uBloom.value = R.bloom ? (R.hdr ? 0.5 : 0.35) : 0; f.uExposure.value = exposure; f.uTime.value = wall; f.uRes.value.set(R.w, R.h);
    pass(mFinal, null);
  };
  return R;
}
