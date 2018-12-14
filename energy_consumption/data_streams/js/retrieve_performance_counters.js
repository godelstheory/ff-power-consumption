async function promiseSnapshot() {

    let addons = WebExtensionPolicy.getActiveExtensions();
    let addonHosts = new Map();
    for (let addon of addons)
      addonHosts.set(addon.mozExtensionHostname, addon.id);

    let counters = await ChromeUtils.requestPerformanceMetrics();
    let tabs = {};
    for (let counter of counters) {
      let {items, host, pid, counterId, windowId, duration, isWorker,
           memoryInfo, isTopLevel} = counter;
      // If a worker has a windowId of 0 or max uint64, attach it to the
      // browser UI (doc group with id 1).
      if (isWorker && (windowId == 18446744073709552000 || !windowId))
        windowId = 1;
      let dispatchCount = 0;
      for (let {count} of items) {
        dispatchCount += count;
      }

      let memory = 0;
      for (let field in memoryInfo) {
        if (field == "media") {
          for (let mediaField of ["audioSize", "videoSize", "resourcesSize"]) {
            memory += memoryInfo.media[mediaField];
          }
          continue;
        }
        memory += memoryInfo[field];
      }

      let tab;
      let id = windowId;
      if (addonHosts.has(host)) {
        id = addonHosts.get(host);
      }
      if (id in tabs) {
        tab = tabs[id];
      } else {
        tab = {windowId, host, dispatchCount: 0, duration: 0, memory: 0, children: []};
        tabs[id] = tab;
      }
      tab.dispatchCount += dispatchCount;
      tab.duration += duration;
      tab.memory += memory;
      if (!isTopLevel || isWorker) {
        tab.children.push({host, isWorker, dispatchCount, duration, memory,
                           counterId: pid + ":" + counterId});
      }
    }

    return {tabs, date: Cu.now()};
}
return promiseSnapshot();