#[rustfmt::skip]

use anyhow::Result;

use ic_tests::driver::group::SystemTestGroup;
use ic_tests::{ckbtc, systest};

fn main() -> Result<()> {
    SystemTestGroup::new()
        .with_setup(ckbtc::lib::config)
        .add_test(systest!(
            ckbtc::minter::test_retrieve_btc::test_retrieve_btc
        ))
        .execute_from_args()?;
    Ok(())
}
