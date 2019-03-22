async function promiseSnapshot() {

    let process = await ChromeUtils.requestProcInfo();
    return {process, date: Cu.now()};
}
return promiseSnapshot();
