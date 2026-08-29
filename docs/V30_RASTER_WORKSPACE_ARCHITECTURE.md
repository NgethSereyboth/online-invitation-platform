# V30 Raster Workspace — Architecture Plan Only

V30 should add a worker/tile-based nondestructive pixel engine with bounded memory, brush, eraser, healing, clone stamp, true crop coordinates, convolution/sharpening, object removal/content-aware fill, a filter graph, and GPU/CPU parity. Originals remain immutable and derivatives are authorized stored objects. No V30 implementation is included in V28.0.
