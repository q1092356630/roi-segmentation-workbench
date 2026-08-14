(function () {
  'use strict';

  const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));

  function perspective(fieldOfView, aspect, near, far) {
    const f = 1 / Math.tan(fieldOfView / 2);
    const rangeInverse = 1 / (near - far);
    return new Float32Array([
      f / aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (near + far) * rangeInverse, -1,
      0, 0, near * far * rangeInverse * 2, 0,
    ]);
  }

  function normalize(vector) {
    const length = Math.hypot(vector[0], vector[1], vector[2]) || 1;
    return [vector[0] / length, vector[1] / length, vector[2] / length];
  }

  function cross(left, right) {
    return [
      left[1] * right[2] - left[2] * right[1],
      left[2] * right[0] - left[0] * right[2],
      left[0] * right[1] - left[1] * right[0],
    ];
  }

  function lookAt(eye, target, up) {
    const zAxis = normalize([eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]]);
    const xAxis = normalize(cross(up, zAxis));
    const yAxis = cross(zAxis, xAxis);
    return new Float32Array([
      xAxis[0], yAxis[0], zAxis[0], 0,
      xAxis[1], yAxis[1], zAxis[1], 0,
      xAxis[2], yAxis[2], zAxis[2], 0,
      -(xAxis[0] * eye[0] + xAxis[1] * eye[1] + xAxis[2] * eye[2]),
      -(yAxis[0] * eye[0] + yAxis[1] * eye[1] + yAxis[2] * eye[2]),
      -(zAxis[0] * eye[0] + zAxis[1] * eye[1] + zAxis[2] * eye[2]),
      1,
    ]);
  }

  function multiply(left, right) {
    const result = new Float32Array(16);
    for (let column = 0; column < 4; column += 1) {
      for (let row = 0; row < 4; row += 1) {
        result[column * 4 + row] =
          left[row] * right[column * 4]
          + left[4 + row] * right[column * 4 + 1]
          + left[8 + row] * right[column * 4 + 2]
          + left[12 + row] * right[column * 4 + 3];
      }
    }
    return result;
  }

  function createShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader) || '未知着色器错误';
      gl.deleteShader(shader);
      throw new Error(`3D 着色器编译失败：${message}`);
    }
    return shader;
  }

  function createProgram(gl) {
    const vertexShader = createShader(gl, gl.VERTEX_SHADER, `#version 300 es
      in vec3 aPosition;
      in vec3 aNormal;
      uniform mat4 uViewProjection;
      out vec3 vNormal;
      void main() {
        vNormal = aNormal;
        gl_Position = uViewProjection * vec4(aPosition, 1.0);
      }
    `);
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, `#version 300 es
      precision highp float;
      in vec3 vNormal;
      uniform vec3 uColor;
      uniform float uOpacity;
      uniform vec3 uLightDirection;
      out vec4 outputColor;
      void main() {
        vec3 normal = normalize(vNormal);
        float diffuse = max(dot(normal, normalize(uLightDirection)), 0.0);
        float backLight = max(dot(normal, normalize(-uLightDirection)), 0.0) * 0.18;
        float lighting = 0.30 + diffuse * 0.62 + backLight;
        vec3 color = clamp(uColor * lighting + vec3(0.035), 0.0, 1.0);
        outputColor = vec4(color, uOpacity);
      }
    `);
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const message = gl.getProgramInfoLog(program) || '未知链接错误';
      gl.deleteProgram(program);
      throw new Error(`3D 渲染程序初始化失败：${message}`);
    }
    return program;
  }

  class Roi3DRenderer {
    constructor(canvas) {
      if (!(canvas instanceof HTMLCanvasElement)) throw new Error('3D 画布不存在');
      this.canvas = canvas;
      this.gl = canvas.getContext('webgl2', {
        antialias: true,
        alpha: false,
        depth: true,
        premultipliedAlpha: false,
        preserveDrawingBuffer: false,
      });
      if (!this.gl) throw new Error('当前浏览器不支持 WebGL2；2D ROI 勾画仍可继续使用');

      const gl = this.gl;
      this.program = createProgram(gl);
      this.locations = {
        position: gl.getAttribLocation(this.program, 'aPosition'),
        normal: gl.getAttribLocation(this.program, 'aNormal'),
        viewProjection: gl.getUniformLocation(this.program, 'uViewProjection'),
        color: gl.getUniformLocation(this.program, 'uColor'),
        opacity: gl.getUniformLocation(this.program, 'uOpacity'),
        lightDirection: gl.getUniformLocation(this.program, 'uLightDirection'),
      };
      this.meshes = [];
      this.indexCount = 0;
      this.objectRadius = 1;
      this.theta = 0.72;
      this.phi = 1.08;
      this.distance = 3;
      this.color = [0.1725, 0.7176, 0.6431];
      this.opacity = 0.78;
      this.clearColor = [0.015, 0.027, 0.039, 1];
      this.dragging = false;
      this.pointerId = null;
      this.lastPointer = { x: 0, y: 0 };
      this.frame = null;

      this.bindEvents();
      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(canvas.parentElement || canvas);
      this.resize();
    }

    bindEvents() {
      this.canvas.addEventListener('contextmenu', event => event.preventDefault());
      this.canvas.addEventListener('pointerdown', event => {
        if (event.button !== 0) return;
        this.dragging = true;
        this.pointerId = event.pointerId;
        this.lastPointer = { x: event.clientX, y: event.clientY };
        this.canvas.setPointerCapture(event.pointerId);
      });
      this.canvas.addEventListener('pointermove', event => {
        if (!this.dragging || event.pointerId !== this.pointerId) return;
        const deltaX = event.clientX - this.lastPointer.x;
        const deltaY = event.clientY - this.lastPointer.y;
        this.lastPointer = { x: event.clientX, y: event.clientY };
        this.theta -= deltaX * 0.008;
        this.phi = clamp(this.phi - deltaY * 0.008, 0.08, Math.PI - 0.08);
        this.requestRender();
      });
      const release = event => {
        if (event.pointerId !== this.pointerId) return;
        this.dragging = false;
        this.pointerId = null;
      };
      this.canvas.addEventListener('pointerup', release);
      this.canvas.addEventListener('pointercancel', release);
      this.canvas.addEventListener('wheel', event => {
        event.preventDefault();
        this.distance = clamp(
          this.distance * Math.exp(event.deltaY * 0.001),
          this.objectRadius * 1.15,
          this.objectRadius * 9,
        );
        this.requestRender();
      }, { passive: false });
      this.canvas.addEventListener('keydown', event => {
        const rotationStep = Math.PI / 24;
        if (event.key === 'ArrowLeft') this.theta += rotationStep;
        else if (event.key === 'ArrowRight') this.theta -= rotationStep;
        else if (event.key === 'ArrowUp') this.phi = clamp(this.phi - rotationStep, 0.08, Math.PI - 0.08);
        else if (event.key === 'ArrowDown') this.phi = clamp(this.phi + rotationStep, 0.08, Math.PI - 0.08);
        else if (event.key === '+' || event.key === '=') this.distance = Math.max(this.objectRadius * 1.15, this.distance * 0.88);
        else if (event.key === '-' || event.key === '_') this.distance = Math.min(this.objectRadius * 9, this.distance * 1.12);
        else if (event.key === '0') this.resetView();
        else return;
        event.preventDefault();
        this.requestRender();
      });
    }

    setMeshes(meshes) {
      if (!Array.isArray(meshes) || !meshes.length) throw new Error('没有可显示的三维 ROI');
      meshes.forEach(mesh => {
        if (!mesh || !Array.isArray(mesh.vertices) || !Array.isArray(mesh.normals) || !Array.isArray(mesh.indices)) {
          throw new Error('三维网格数据格式无效');
        }
        if (!mesh.vertices.length || mesh.vertices.length % 3 || mesh.normals.length !== mesh.vertices.length || mesh.indices.length % 3) {
          throw new Error('三维网格数据不完整');
        }
      });
      const minimum = [0, 1, 2].map(axis => Math.min(...meshes.map(mesh => Number(mesh.bounds_mm?.min?.[axis]))));
      const maximum = [0, 1, 2].map(axis => Math.max(...meshes.map(mesh => Number(mesh.bounds_mm?.max?.[axis]))));
      const center = [
        (Number(minimum[0]) + Number(maximum[0])) / 2,
        (Number(minimum[1]) + Number(maximum[1])) / 2,
        (Number(minimum[2]) + Number(maximum[2])) / 2,
      ];
      const extents = [
        Number(maximum[0]) - Number(minimum[0]),
        Number(maximum[1]) - Number(minimum[1]),
        Number(maximum[2]) - Number(minimum[2]),
      ];
      if (![...center, ...extents].every(Number.isFinite) || extents.some(value => value <= 0)) {
        throw new Error('三维网格包围盒无效');
      }
      const gl = this.gl;
      this.clearMesh(false);
      this.meshes = meshes.map(mesh => {
        const vertices = new Float32Array(mesh.vertices);
        const normals = new Float32Array(mesh.normals);
        const indices = new Uint32Array(mesh.indices);
        for (let index = 0; index < vertices.length; index += 3) {
          vertices[index] -= center[0];
          vertices[index + 1] -= center[1];
          vertices[index + 2] -= center[2];
        }
        const vertexArray = gl.createVertexArray();
        const positionBuffer = gl.createBuffer();
        const normalBuffer = gl.createBuffer();
        const indexBuffer = gl.createBuffer();
        gl.bindVertexArray(vertexArray);
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(this.locations.position);
        gl.vertexAttribPointer(this.locations.position, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, normals, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(this.locations.normal);
        gl.vertexAttribPointer(this.locations.normal, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
        return {
          vertexArray, positionBuffer, normalBuffer, indexBuffer,
          labelId: Number(mesh.label_id),
          layerKey: String(mesh.layer_key || ''),
          indexCount: indices.length,
          color: this.parseColor(mesh.render_color || mesh.label_color || '#2cb7a4'),
        };
      });
      gl.bindVertexArray(null);
      this.indexCount = this.meshes.reduce((sum, mesh) => sum + mesh.indexCount, 0);
      this.objectRadius = Math.max(0.5, Math.hypot(extents[0], extents[1], extents[2]) / 2);
      this.resetView();
    }

    setMesh(mesh) {
      this.setMeshes([{ ...mesh, render_color: mesh.render_color || this.toHexColor(this.color) }]);
    }

    clearMesh(render = true) {
      const gl = this.gl;
      this.meshes.forEach(mesh => {
        gl.deleteVertexArray(mesh.vertexArray);
        gl.deleteBuffer(mesh.positionBuffer);
        gl.deleteBuffer(mesh.normalBuffer);
        gl.deleteBuffer(mesh.indexBuffer);
      });
      this.meshes = [];
      this.indexCount = 0;
      if (render) this.requestRender();
    }

    parseColor(hexColor) {
      if (!/^#[0-9a-f]{6}$/i.test(hexColor || '')) throw new Error('3D 颜色必须使用 #RRGGBB');
      return [1, 3, 5].map(offset => parseInt(hexColor.slice(offset, offset + 2), 16) / 255);
    }

    toHexColor(color) {
      return `#${color.map(value => Math.round(clamp(value, 0, 1) * 255).toString(16).padStart(2, '0')).join('')}`;
    }

    setColor(hexColor) {
      this.color = this.parseColor(hexColor);
      if (this.meshes.length === 1) this.meshes[0].color = [...this.color];
      this.requestRender();
    }

    setMeshColor(labelId, hexColor) {
      const key = String(labelId || '');
      const mesh = this.meshes.find(item => (item.layerKey && item.layerKey === key) || item.labelId === Number(labelId));
      if (!mesh) return false;
      mesh.color = this.parseColor(hexColor);
      this.requestRender();
      return true;
    }

    setOpacity(opacity) {
      this.opacity = clamp(Number(opacity), 0.1, 1);
      this.requestRender();
    }

    setTheme(theme) {
      this.clearColor = theme === 'light' ? [0.89, 0.925, 0.945, 1] : [0.015, 0.027, 0.039, 1];
      this.requestRender();
    }

    resetView() {
      this.theta = 0.72;
      this.phi = 1.08;
      this.distance = this.objectRadius * 2.8;
      this.requestRender();
    }

    resize() {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(this.canvas.clientWidth * ratio));
      const height = Math.max(1, Math.round(this.canvas.clientHeight * ratio));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
      this.requestRender();
    }

    requestRender() {
      if (this.frame !== null) return;
      this.frame = requestAnimationFrame(() => {
        this.frame = null;
        this.render();
      });
    }

    render() {
      const gl = this.gl;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      gl.clearColor(...this.clearColor);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      if (!this.indexCount) return;

      const sinPhi = Math.sin(this.phi);
      const eye = [
        this.distance * sinPhi * Math.sin(this.theta),
        this.distance * Math.cos(this.phi),
        this.distance * sinPhi * Math.cos(this.theta),
      ];
      const near = Math.max(0.01, this.distance - this.objectRadius * 2.2);
      const far = this.distance + this.objectRadius * 3.2;
      const projection = perspective(Math.PI / 4, this.canvas.width / this.canvas.height, near, far);
      const view = lookAt(eye, [0, 0, 0], [0, 1, 0]);
      const viewProjection = multiply(projection, view);

      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      if (this.opacity < 0.995) {
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.depthMask(false);
      } else {
        gl.disable(gl.BLEND);
        gl.depthMask(true);
      }
      gl.useProgram(this.program);
      gl.uniformMatrix4fv(this.locations.viewProjection, false, viewProjection);
      gl.uniform1f(this.locations.opacity, this.opacity);
      gl.uniform3fv(this.locations.lightDirection, [0.42, 0.72, 0.56]);
      this.meshes.forEach(mesh => {
        gl.bindVertexArray(mesh.vertexArray);
        gl.uniform3fv(this.locations.color, mesh.color);
        gl.drawElements(gl.TRIANGLES, mesh.indexCount, gl.UNSIGNED_INT, 0);
      });
      gl.bindVertexArray(null);
      gl.depthMask(true);
    }
  }

  window.Roi3DRenderer = Roi3DRenderer;
}());
