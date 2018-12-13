async function promiseSnapshot() {
    let counters = await ChromeUtils.requestPerformanceMetrics();
    let tabs = {};
    for (let counter of counters) {
      let {items, host, windowId, duration, isWorker, isTopLevel} = counter;
      // If a worker has a windowId of 0 or max uint64, attach it to the
      // browser UI (doc group with id 1).
      if (isWorker && (windowId == 18446744073709552000 || !windowId))
        windowId = 1;
      let dispatchCount = 0;
      for (let {count} of items) {
        dispatchCount += count;
      }
      let tab;
      if (windowId in tabs) {
        tab = tabs[windowId];
      } else {
        tab = {windowId, host, dispatchCount: 0, duration: 0, children: []};
        tabs[windowId] = tab
      }
      tab.dispatchCount += dispatchCount;
      tab.duration += duration;
      if (!isTopLevel) {
        tab.children.push({host, isWorker, dispatchCount, duration});
      }
    }
    return tabs;
}
return promiseSnapshot();