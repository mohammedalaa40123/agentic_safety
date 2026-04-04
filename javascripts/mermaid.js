document$.subscribe(function () {
  mermaid.initialize({
    startOnLoad: true,
    theme: "neutral",
    securityLevel: "loose"
  });
  mermaid.run();
});
