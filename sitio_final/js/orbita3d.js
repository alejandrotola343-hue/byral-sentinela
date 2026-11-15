(function () {
  const container = document.getElementById('space-canvas');
  if (!container || !window.THREE) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(-1.35, 0.35, 5.4);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  container.appendChild(renderer.domElement);

  const loader = new THREE.TextureLoader();
  loader.setCrossOrigin('anonymous');

  const texDay = loader.load('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg');
  const texBump = loader.load('https://unpkg.com/three-globe/example/img/earth-topology.png');
  const texNight = loader.load('https://unpkg.com/three-globe/example/img/earth-night.jpg');
  const texClouds = loader.load('https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_clouds_1024.png');

  const earthGroup = new THREE.Group();
  earthGroup.position.set(-2.6, -0.05, 0);
  earthGroup.rotation.z = THREE.MathUtils.degToRad(23.44);
  scene.add(earthGroup);

  const sunDir = new THREE.Vector3(1.0, 0.25, 0.7).normalize();

  const earthMat = new THREE.ShaderMaterial({
    uniforms: {
      dayTexture: { value: texDay },
      nightTexture: { value: texNight },
      bumpMap: { value: texBump },
      sunDirection: { value: sunDir }
    },
    vertexShader: 'varying vec2 vUv; varying vec3 vNormalWorld; varying vec3 vPosWorld; void main() { vUv = uv; vec4 worldPos = modelMatrix * vec4(position, 1.0); vPosWorld = worldPos.xyz; vNormalWorld = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * worldPos; }',
    fragmentShader: 'uniform sampler2D dayTexture; uniform sampler2D nightTexture; uniform sampler2D bumpMap; uniform vec3 sunDirection; varying vec2 vUv; varying vec3 vNormalWorld; varying vec3 vPosWorld; void main() { vec3 N = normalize(vNormalWorld); vec3 L = normalize(sunDirection); vec3 V = normalize(cameraPosition - vPosWorld); float ndotl = dot(N, L); float dayFactor = smoothstep(-0.18, 0.28, ndotl); vec3 dayCol = texture2D(dayTexture, vUv).rgb; vec3 nightCol = texture2D(nightTexture, vUv).rgb; float elev = texture2D(bumpMap, vUv).r; vec3 H = normalize(L + V); float spec = pow(max(dot(N, H), 0.0), 48.0) * (1.0 - smoothstep(0.02, 0.14, elev)) * dayFactor; vec3 litDay = dayCol * (0.14 + 1.08 * max(ndotl, 0.0)) + vec3(0.45, 0.62, 0.85) * spec * 0.55; float nightMask = 1.0 - smoothstep(-0.22, 0.12, ndotl); vec3 cityLights = pow(nightCol, vec3(1.15)) * vec3(1.55, 1.18, 0.72) * nightMask * 1.45; float twilight = exp(-pow((ndotl + 0.02) * 8.5, 2.0)); vec3 rimTwilight = vec3(0.85, 0.36, 0.14) * twilight * 0.16; gl_FragColor = vec4(litDay + cityLights + rimTwilight, 1.0); }'
  });

  const earthMesh = new THREE.Mesh(new THREE.SphereGeometry(1.78, 96, 96), earthMat);
  earthGroup.add(earthMesh);

  const cloudMat = new THREE.MeshPhongMaterial({
    map: texClouds,
    transparent: true,
    opacity: 0.52,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  });
  const cloudMesh = new THREE.Mesh(new THREE.SphereGeometry(1.805, 80, 80), cloudMat);
  earthGroup.add(cloudMesh);

  const atmoMat = new THREE.ShaderMaterial({
    transparent: true,
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    vertexShader: 'varying vec3 vNormal; void main() { vNormal = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'varying vec3 vNormal; void main() { float intensity = pow(0.66 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.2); gl_FragColor = vec4(0.24, 0.62, 1.0, 1.0) * intensity * 1.15; }'
  });
  earthGroup.add(new THREE.Mesh(new THREE.SphereGeometry(1.93, 64, 64), atmoMat));

  const sunLight = new THREE.DirectionalLight(0xffffff, 1.35);
  sunLight.position.set(6, 1.8, 4.5);
  scene.add(sunLight);
  scene.add(new THREE.AmbientLight(0x16243d, 0.45));

  const starGeo = new THREE.BufferGeometry();
  const starCount = 2600;
  const starPos = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount * 3; i++) starPos[i] = (Math.random() - 0.5) * 90;
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
  scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xdbeafe, size: 0.075, transparent: true, opacity: 0.85 })));

  function latLngToVec3(lat, lng, r) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);
    return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
  }

  const cbbaBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.026, 16, 16), new THREE.MeshBasicMaterial({ color: 0x38bdf8 }));
  cbbaBeacon.position.copy(latLngToVec3(-17.3935, -66.1570, 1.81));
  earthMesh.add(cbbaBeacon);

  const weatherCellsGroup = new THREE.Group();
  earthMesh.add(weatherCellsGroup);

  window.actualizarClimaEnGlobo3D = function (stations) {
    while (weatherCellsGroup.children.length > 0) weatherCellsGroup.remove(weatherCellsGroup.children[0]);
    (stations || []).forEach(st => {
      if (st.rain > 0) {
        const cell = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 16), new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.55 }));
        cell.position.copy(latLngToVec3(st.lat, st.lng, 1.818));
        weatherCellsGroup.add(cell);
      }
    });
  };

  function updateOrbitalTelemetry() {
    const now = new Date();
    const utcEl = document.getElementById('utc-clock-txt');
    const gmstEl = document.getElementById('gmst-txt');
    if (utcEl) utcEl.innerText = now.toISOString().substr(11, 8) + ' UTC';
    const jd = now.getTime() / 86400000 + 2440587.5;
    const gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360;
    if (gmstEl) gmstEl.innerText = ((gmst + 360) % 360).toFixed(2) + '°';
    const utcHours = now.getUTCHours() + now.getUTCMinutes() / 60;
    const sunLon = ((12 - utcHours) * 15) * (Math.PI / 180);
    sunDir.set(Math.cos(sunLon), 0.18, -Math.sin(sunLon)).normalize();
    earthMat.uniforms.sunDirection.value.copy(sunDir);
    sunLight.position.copy(sunDir).multiplyScalar(8);
  }

  earthMesh.rotation.y = THREE.MathUtils.degToRad(-24);

  function animate() {
    requestAnimationFrame(animate);
    earthMesh.rotation.y += 0.00085;
    cloudMesh.rotation.y += 0.00115;
    updateOrbitalTelemetry();
    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
})();