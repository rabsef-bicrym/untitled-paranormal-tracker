# Spike: Visualization Library Comparison - D3.js vs deck.gl

**Date:** January 2026
**Issue:** upt-9a5
**Objective:** Evaluate D3.js and deck.gl for rendering a 2D scatter plot with 10k+ data points

---

## Executive Summary

**Recommendation: deck.gl** for this use case.

deck.gl is purpose-built for large dataset visualization using WebGL2/WebGPU and handles 10k+ points with ease (benchmarked at 60 FPS with up to 1 million points). While D3.js offers more flexibility for custom visualizations, it requires additional complexity (Canvas or WebGL rendering via D3FC) to achieve comparable performance at this scale. For a straightforward scatter plot with 10k+ interactive points, deck.gl provides the better out-of-box experience.

---

## Comparison Matrix

| Criteria | D3.js | deck.gl | Winner |
|----------|-------|---------|--------|
| **10k+ point performance** | Requires Canvas/WebGL | Native 60 FPS | deck.gl |
| **Interactivity** | Full control, more work | Built-in hover/click/zoom | deck.gl |
| **Bundle size** | ~75-100kb (tree-shaken) | ~200-300kb (core + layers) | D3.js |
| **Learning curve** | Steep | Moderate | deck.gl |
| **Mobile performance** | Good (Canvas) | Good with tuning | Tie |
| **Next.js 14 integration** | Straightforward | Minor SSR issues | D3.js |

---

## 1. Performance with 10k+ Points

### D3.js
- **SVG rendering**: Practical limit of ~1,000 elements before performance degrades
- **Canvas rendering**: Can handle ~10,000 points while maintaining 60 FPS interactions
- **WebGL via D3FC**: Can render 1 million+ points at 60 FPS, but requires additional library integration

D3.js with standard SVG would struggle with 10k points. You would need to use Canvas or integrate with D3FC (WebGL) to achieve smooth performance.

> "SVG charts can typically handle around 1,000 datapoints. Since D3 v4 you've also had the option to render charts using canvas... With Canvas you can expect to render around 10,000 datapoints whilst maintaining smooth 60fps interactions." - [Scott Logic](https://blog.scottlogic.com/2020/05/01/rendering-one-million-points-with-d3.html)

### deck.gl
- **ScatterplotLayer**: Renders 1 million points at 60 FPS on 2015-era MacBooks
- Performance drops to 10-20 FPS only when approaching 10 million items
- WebGL2/WebGPU rendering is the default, no additional setup needed

> "Most basic layers (like ScatterplotLayer) render fluidly at 60 FPS during pan and zoom operations up to about 1M (one million) data items." - [deck.gl Performance Docs](https://deck.gl/docs/developer-guide/performance)

**Verdict**: deck.gl handles 10k points trivially. D3.js needs Canvas or WebGL integration.

---

## 2. Interactivity (Zoom, Pan, Click, Hover)

### D3.js
- Complete control over interaction implementation
- Must manually implement zoom/pan behaviors with `d3-zoom`
- Click and hover require custom event binding to SVG/Canvas elements
- More code, but maximum flexibility

### deck.gl
- Built-in `pickable` prop enables hover and click detection
- Automatic coordinate projection for picked objects
- Pan and zoom handled by the view system
- Integrates with map libraries (Mapbox, MapLibre) for geospatial zoom

```javascript
// deck.gl - hover/click with minimal code
new ScatterplotLayer({
  data,
  pickable: true,
  onHover: (info) => setTooltip(info.object),
  onClick: (info) => handleClick(info.object),
})
```

**Verdict**: deck.gl provides interactivity out of the box. D3.js requires manual implementation.

---

## 3. Bundle Size Impact

### D3.js
- Full package: ~509 kB (unminified), ~250 kB (minified), ~75 kB (gzipped)
- Tree-shakeable via submodule imports
- For a scatter plot, you might only need: `d3-selection`, `d3-scale`, `d3-axis`, `d3-zoom` (~50-80 kB gzipped)

```javascript
// Optimized D3 imports
import { select } from 'd3-selection';
import { scaleLinear } from 'd3-scale';
import { axisBottom, axisLeft } from 'd3-axis';
```

### deck.gl
- Full package: ~1.2 MB (minified), ~300-400 kB (gzipped)
- Modular architecture with tree-shaking support
- Minimum for scatter plot: `@deck.gl/core` + `@deck.gl/layers` (~200-250 kB gzipped)
- v8.0 reduced `@deck.gl/core` by 50 kB compared to v7.3

**Verdict**: D3.js has a smaller footprint, especially with selective imports.

---

## 4. Learning Curve / Implementation Time

### D3.js
- **Steep learning curve** - requires understanding SVG, DOM manipulation, data binding, scales, axes
- Method chaining and "enter/update/exit" pattern is unfamiliar to most developers
- Estimated time to first scatter plot: 4-8 hours for beginners
- Estimated time for production-ready interactive chart: 2-3 days

> "D3.js has a steep learning curve... You just don't get to build things right out of the box with D3. With its confusing method chains, alien syntax, and black-box functions that seem to work by magic, D3 can quickly seem like more hassle than it's worth." - [Hackr.io](https://hackr.io/tutorials/learn-d3-js)

### deck.gl
- **Moderate learning curve** - declarative layer API similar to React props
- Composable layers work like components
- WebGL knowledge NOT required for using built-in layers
- Estimated time to first scatter plot: 1-2 hours
- Estimated time for production-ready chart: 1 day

```javascript
// deck.gl - complete scatter plot in ~20 lines
import { Deck } from '@deck.gl/core';
import { ScatterplotLayer } from '@deck.gl/layers';

new Deck({
  initialViewState: { longitude: 0, latitude: 0, zoom: 1 },
  controller: true,
  layers: [
    new ScatterplotLayer({
      data: points,
      getPosition: d => [d.x, d.y],
      getRadius: 5,
      getFillColor: [255, 140, 0],
    })
  ]
});
```

**Verdict**: deck.gl is faster to get started with for this use case.

---

## 5. Mobile Performance

### D3.js
- Canvas rendering works well on mobile
- SVG struggles with many elements (DOM overhead)
- No special mobile considerations beyond standard responsive design
- Touch events need explicit handling

### deck.gl
- WebGL renders efficiently on modern mobile GPUs
- Memory pressure is the main concern (mobile browsers are more sensitive)
- Recommend disabling retina resolution for 4x render buffer reduction:

```javascript
new Deck({
  useDevicePixels: false, // Reduces memory on retina displays
  // ...
});
```

- Touch interactions (pinch zoom, pan) work automatically
- May need data loading optimization for slow mobile networks

> "Modern phones are surprisingly capable in terms of rendering performance, but are considerably more sensitive to memory pressure than laptops, resulting in browser restarts or page reloads." - [deck.gl Performance Docs](https://deck.gl/docs/developer-guide/performance)

**Verdict**: Both perform adequately on mobile with appropriate optimizations.

---

## 6. Integration with Next.js 14 App Router

### D3.js
- Works well with Next.js App Router
- Use `"use client"` directive for D3 components
- No SSR issues since D3 manipulates DOM in useEffect
- Standard pattern:

```javascript
"use client";
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export function ScatterPlot({ data }) {
  const svgRef = useRef();

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    // D3 rendering logic
  }, [data]);

  return <svg ref={svgRef} />;
}
```

### deck.gl
- Has React bindings via `@deck.gl/react`
- Reported ES module issues with Next.js (`require() of ES module` error)
- Workarounds available but require configuration
- Use dynamic imports with `ssr: false`:

```javascript
"use client";
import dynamic from 'next/dynamic';

const DeckGL = dynamic(
  () => import('@deck.gl/react').then(mod => mod.DeckGL),
  { ssr: false }
);
```

> "There's a documented bug when trying to add deck.gl to a Next.js project... can result in a 'require() of ES module' error." - [GitHub Issue #7773](https://github.com/visgl/deck.gl/issues/7773)

**Verdict**: D3.js integrates more smoothly; deck.gl requires SSR workarounds.

---

## Recommendation

**Use deck.gl** for this project.

### Rationale

1. **Performance is the primary concern**: 10k+ points is deck.gl's sweet spot. D3.js would require Canvas or WebGL integration to match.

2. **Faster implementation**: deck.gl's `ScatterplotLayer` provides exactly what we need with built-in interactivity. D3.js would require significantly more code.

3. **Bundle size is acceptable**: The ~150-200 kB difference is negligible for a data visualization app where users expect some loading time.

4. **Next.js SSR issues are solvable**: Dynamic imports with `ssr: false` is a standard pattern and well-documented.

### When to Choose D3.js Instead

- If you need highly custom, non-standard visualizations
- If bundle size is critical (e.g., embedded widget)
- If you're already experienced with D3.js
- If you need to render static charts (SSR-friendly)

---

## Implementation Notes

### Recommended deck.gl Setup

```bash
npm install @deck.gl/core @deck.gl/layers @deck.gl/react
```

### Minimal Scatter Plot Component

```typescript
"use client";

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { ScatterplotLayer } from '@deck.gl/layers';

const DeckGL = dynamic(
  () => import('@deck.gl/react').then(mod => mod.DeckGL),
  { ssr: false }
);

interface DataPoint {
  position: [number, number];
  value: number;
}

export function ScatterPlot({ data }: { data: DataPoint[] }) {
  const [viewState, setViewState] = useState({
    longitude: 0,
    latitude: 0,
    zoom: 1,
  });

  const layers = [
    new ScatterplotLayer({
      id: 'scatter',
      data,
      pickable: true,
      opacity: 0.8,
      filled: true,
      radiusScale: 6,
      radiusMinPixels: 1,
      radiusMaxPixels: 100,
      getPosition: (d: DataPoint) => d.position,
      getRadius: 5,
      getFillColor: (d: DataPoint) => [255, 140, 0, 200],
    }),
  ];

  return (
    <DeckGL
      viewState={viewState}
      onViewStateChange={({ viewState }) => setViewState(viewState)}
      controller={true}
      layers={layers}
    />
  );
}
```

---

## Sources

- [deck.gl Performance Optimization](https://deck.gl/docs/developer-guide/performance)
- [deck.gl Getting Started](https://deck.gl/docs/get-started/getting-started)
- [Rendering One Million Points with D3 and WebGL](https://blog.scottlogic.com/2020/05/01/rendering-one-million-points-with-d3.html)
- [D3.js Official Documentation](https://d3js.org/)
- [deck.gl React Integration](https://deck.gl/docs/get-started/using-with-react)
- [deck.gl Next.js Issues](https://github.com/visgl/deck.gl/issues/7773)
- [Bundlephobia - D3](https://bundlephobia.com/package/d3)
- [Bundlephobia - deck.gl](https://bundlephobia.com/package/deck.gl)
