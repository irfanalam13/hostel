// Vitest assertion augmentation for @testing-library/jest-dom matchers
// (toBeInTheDocument etc.). Referenced by every workspace tsconfig so test
// files type-check without importing the runtime setup file.
import "@testing-library/jest-dom/vitest";
